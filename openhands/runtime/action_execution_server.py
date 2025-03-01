"""
This is the main file for the runtime client.
It is responsible for executing actions received from OpenHands backend and producing observations.

NOTE: this will be executed inside the docker sandbox.
"""

import argparse
import asyncio
import base64
import json
import mimetypes
import os
import re
import shutil
import sys
import tempfile
import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from zipfile import ZipFile

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
# from openhands_aci.utils.diff import get_diff
from pydantic import BaseModel
from starlette.background import BackgroundTask
from starlette.exceptions import HTTPException as StarletteHTTPException
from uvicorn import run

from openhands.core.logger import openhands_logger as logger
from openhands.events.action import (
    Action,
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
    IPythonRunCellAction,
)
from openhands.events.event import FileEditSource, FileReadSource
from openhands.events.observation import (
    CmdOutputObservation,
    ErrorObservation,
    FileEditObservation,
    FileReadObservation,
    FileWriteObservation,
    Observation,
)
from openhands.events.observation.commands import IPythonRunCellObservation
from openhands.events.serialization import event_from_dict, event_to_dict
from openhands.runtime.browser import browse
from openhands.runtime.browser.browser_env import BrowserEnv
from openhands.runtime.plugins import ALL_PLUGINS, JupyterPlugin, Plugin, VSCodePlugin
if os.environ.get('USE_PEXPECT') == '1' or 1:
    from openhands.runtime.utils.bash_pexpect import BashSession
else:        
    from openhands.runtime.utils.bash import BashSession
from openhands.runtime.utils.files import insert_lines, read_lines
from openhands.runtime.utils.memory_monitor import MemoryMonitor
from openhands.runtime.utils.runtime_init import init_user_and_working_directory
from openhands.runtime.utils.system_stats import get_system_stats
from openhands.utils.async_utils import call_sync_from_async, wait_all


class ActionRequest(BaseModel):
    action: dict


ROOT_GID = 0

SESSION_API_KEY = os.environ.get('SESSION_API_KEY')
api_key_header = APIKeyHeader(name='X-Session-API-Key', auto_error=False)


def verify_api_key(api_key: str = Depends(api_key_header)):
    if SESSION_API_KEY and api_key != SESSION_API_KEY:
        raise HTTPException(status_code=403, detail='Invalid API Key')
    return api_key



class ActionExecutor:
    """ActionExecutor is running inside docker sandbox.
    It is responsible for executing actions received from OpenHands backend and producing observations.
    """

    def __init__(
        self,
        plugins_to_load: list[Plugin],
        work_dir: str,
        username: str,
        user_id: int,
        browsergym_eval_env: str | None,
    ) -> None:
        self.plugins_to_load = plugins_to_load
        self._initial_cwd = work_dir
        self.username = username
        self.user_id = user_id
        _updated_user_id = init_user_and_working_directory(
            username=username, user_id=self.user_id, initial_cwd=work_dir
        )
        if _updated_user_id is not None:
            self.user_id = _updated_user_id

        self.bash_session: BashSession | None = None
        self.lock = asyncio.Lock()
        self.plugins: dict[str, Plugin] = {}
        self.file_editor = ''
        self.browser = BrowserEnv(browsergym_eval_env)
        self.start_time = time.time()
        self.last_execution_time = self.start_time
        self.last_code = ''
        self.is_last_code_error = False
        self._initialized = False

        self.max_memory_gb: int | None = None
        if _override_max_memory_gb := os.environ.get('RUNTIME_MAX_MEMORY_GB', None):
            self.max_memory_gb = int(_override_max_memory_gb)
            logger.info(
                f'Setting max memory to {self.max_memory_gb}GB (according to the RUNTIME_MAX_MEMORY_GB environment variable)'
            )
        else:
            logger.info('No max memory limit set, using all available system memory')

        self.memory_monitor = MemoryMonitor(
            enable=os.environ.get('RUNTIME_MEMORY_MONITOR', 'False').lower()
            in ['true', '1', 'yes']
        )
        self.memory_monitor.start_monitoring()

    @property
    def initial_cwd(self):
        return self._initial_cwd

    async def ainit(self):
        # bash needs to be initialized first
        logger.debug('Initializing bash session')
        self.bash_session = BashSession(
            work_dir=self._initial_cwd,
            username=self.username,
            no_change_timeout_seconds=int(
                os.environ.get('NO_CHANGE_TIMEOUT_SECONDS', 30)
            ),
            max_memory_mb=self.max_memory_gb * 1024 if self.max_memory_gb else None,
        )
        self.bash_session.initialize()
        logger.debug('Bash session initialized')

        await wait_all(
            (self._init_plugin(plugin) for plugin in self.plugins_to_load),
            timeout=30,
        )
        logger.debug('All plugins initialized')

        code = 'from IPython.display import Image'
        obs = await self.run_ipython(IPythonRunCellAction(code=code))
        logger.debug(f'Image import initialized: {obs}')
        # This is a temporary workaround
        # TODO: refactor AgentSkills to be part of JupyterPlugin
        # AFTER ServerRuntime is deprecated
        logger.debug('Initializing AgentSkills')
        if 'agent_skills' in self.plugins and 'jupyter' in self.plugins:
            self.kernel_init_code = (
                'from openhands.runtime.plugins.agent_skills.agentskills import *'
            )
            obs = await self.run_ipython(
                IPythonRunCellAction(code=self.kernel_init_code)
            )
            logger.debug(f'AgentSkills initialized: {obs}')

        logger.debug('Initializing bash commands')
        await self._init_bash_commands()
        logger.debug('Runtime client initialized.')
        self._initialized = True

    @property
    def initialized(self) -> bool:
        return self._initialized

    async def _init_plugin(self, plugin: Plugin):
        assert self.bash_session is not None
        logger.debug(f'Initializing plugin: {plugin.name}')
        await plugin.initialize(self.username)
        self.plugins[plugin.name] = plugin

        if isinstance(plugin, JupyterPlugin):
            await self.run_ipython(
                IPythonRunCellAction(
                    code=f'import os; os.chdir("{self.bash_session.cwd}")'
                )
            )

    async def _init_bash_commands(self):
        is_local_runtime = os.environ.get('LOCAL_RUNTIME_MODE') == '1'
        INIT_COMMANDS = [
            'git config --file ./.git_config user.name "Kevin AI Agent" && git config --file ./.git_config user.email "kevin@zebralock.ai" && alias git="git --no-pager" && export GIT_CONFIG=$(pwd)/.git_config'
            if is_local_runtime
            else 'git config --global user.name "Kevin AI Agent" && git config --global user.email "kevin@zebralock.ai" && alias git="git --no-pager"'
        ]
        INIT_COMMANDS += [
            'export TERM=xterm-256color',
            'set +H',
        ]
        if not is_local_runtime:
            INIT_COMMANDS += [
                'cd /workspace',
                "export PATH=/openhands/poetry/$(ls /openhands/poetry | sed -n '2p')/bin:$PATH",
            ]
        else:
            INIT_COMMANDS += [
                "export PATH=/testbed/.venv/bin::$PATH",
            ]
        logger.debug(f'Initializing by running {len(INIT_COMMANDS)} bash commands...')
        # if root user, skip last command
        if self.username == 'root' and not is_local_runtime:
            INIT_COMMANDS.pop()
        for command in INIT_COMMANDS:
            action = CmdRunAction(command=command)
            action.set_hard_timeout(300)
            logger.debug(f'Executing init command: {command}')
            obs = await self.run(action)
            assert isinstance(obs, CmdOutputObservation)
            logger.debug(
                f'Init command outputs (exit code: {obs.exit_code}): {obs.content}'
            )
            assert obs.exit_code == 0
        logger.debug('Bash init commands completed')

    async def run_action(self, action) -> Observation:
        async with self.lock:
            action_type = action.action
            logger.debug(f'Running action:\n{action}')
            observation = await getattr(self, action_type)(action)
            logger.debug(f'Action output:\n{observation}')
            return observation

    async def run(
        self, action: CmdRunAction
    ) -> CmdOutputObservation | ErrorObservation:
        assert self.bash_session is not None
        obs = await call_sync_from_async(self.bash_session.execute, action)
        return obs

    async def chdir(self):
        assert self.bash_session is not None
        if 'jupyter' not in self.plugins:
            return
        _jupyter_plugin: JupyterPlugin = self.plugins['jupyter']  # type: ignore
        reset_jupyter_cwd_code = f'import os; os.chdir("{self.bash_session.cwd}")'
        _aux_action = IPythonRunCellAction(code=reset_jupyter_cwd_code)
        _reset_obs: IPythonRunCellObservation = await _jupyter_plugin.run(_aux_action)
        logger.debug(
            f'Changed working directory in IPython to: {self.bash_session.cwd}. Output: {_reset_obs}'
        )
        self._jupyter_cwd = self.bash_session.cwd

    async def restart_kernel(self) -> str:
        if 'agent_skills' not in self.plugins:
            return ''

        jupyter_plugin: JupyterPlugin = self.plugins['jupyter']  # type: ignore
        restart_kernel_code = (
            'import IPython\nIPython.Application.instance().kernel.do_shutdown(True)'
        )
        act = IPythonRunCellAction(code=restart_kernel_code)
        obs = await jupyter_plugin.run(act)
        output = obs.content
        if "{'status': 'ok', 'restart': True}" != output.strip():
            print(output)
            output = '\n[Failed to restart the kernel]'
        else:
            output = '\n[Kernel restarted successfully]'

        await self.chdir()
        # re-init the kernel after restart
        logger.info(f'Re-initializing the kernel with {self.kernel_init_code}')
        act = IPythonRunCellAction(code=self.kernel_init_code)
        obs = await jupyter_plugin.run(act)
        logger.info(f'Kernel re-initialized. Output: {obs}')
        return output

    def parse_pip_output(self, code, output) -> str:
        print(output)
        package_names = code.split(' ', 2)[-1]
        parsed_output = output
        if 'Successfully installed' in output:
            parsed_output = '[Package installed successfully]'
            if (
                'Note: you may need to restart the kernel to use updated packages.'
                in output
            ):
                # parsed_output += await self.restart_kernel()
                pass
            else:
                # restart kernel if installed via bash too
                # await self.restart_kernel()
                pass
        else:
            package_names = package_names.split()
            if all(
                f'Requirement already satisfied: {package_name}' in output
                for package_name in package_names
            ):
                plural = 's' if len(package_names) > 1 else ''
                parsed_output = f'[Package{plural} already installed]'

        return parsed_output

    async def run_ipython(self, action: IPythonRunCellAction) -> Observation:
        assert self.bash_session is not None
        if 'jupyter' in self.plugins:
            _jupyter_plugin: JupyterPlugin = self.plugins['jupyter']  # type: ignore
            # This is used to make AgentSkills in Jupyter aware of the
            # current working directory in Bash
            jupyter_cwd = getattr(self, '_jupyter_cwd', None)
            if self.bash_session.cwd != jupyter_cwd:
                await self.chdir()
            obs: Observation | None = None
            if action.code.startswith('%%writefile /tmp/test_task.py'):
                obs = ErrorObservation(
                    "[The content in this file is absolutely correct. Also, you can't modify this test file. You must pass this test case. You should correct the codebase instead.]"
                )
            # not a shell command; false positive
            # elif action.code.startswith('!python'):
            #     obs = ErrorObservation(
            #         "[Don't use Django shell commands in Jupyter Notebook as file changes will not be reflected. Directly run the code in the terminal using <execute_bash>.]"
            #     )
            elif (
                (self.username == 'root')
                and action.code == self.last_code
                and self.is_last_code_error
            ):
                obs = ErrorObservation(
                    '[You are trying to run the same code twice. Please focus and run the correct code.]'
                )

            if obs:
                return obs
            action.code = action.code.replace('!pip', '%pip')
            obs = await _jupyter_plugin.run(action)
            if 'pip install' in action.code:
                obs.content = self.parse_pip_output(action.code, obs.content)
            obs.content = obs.content.rstrip()
            matches = re.findall(
                r'<oh_aci_output_[0-9a-f]{32}>(.*?)</oh_aci_output_[0-9a-f]{32}>',
                obs.content,
                re.DOTALL,
            )
            if matches:
                results: list[str] = []
                if len(matches) == 1:
                    # Use specific actions/observations types
                    match = matches[0]
                    try:
                        result_dict = json.loads(match)
                        if result_dict.get('path'):  # Successful output
                            if (
                                result_dict['new_content'] is not None
                            ):  # File edit commands
                                # diff = get_diff(
                                #     old_contents=result_dict['old_content']
                                #     or '',  # old_content is None when file is created
                                #     new_contents=result_dict['new_content'],
                                #     filepath=result_dict['path'],
                                # )
                                diff = ''
                                return FileEditObservation(
                                    content=diff,
                                    path=result_dict['path'],
                                    old_content=result_dict['old_content'],
                                    new_content=result_dict['new_content'],
                                    prev_exist=result_dict['prev_exist'],
                                    impl_source=FileEditSource.OH_ACI,
                                    formatted_output_and_error=result_dict[
                                        'formatted_output_and_error'
                                    ],
                                )
                            else:  # File view commands
                                return FileReadObservation(
                                    content=result_dict['formatted_output_and_error'],
                                    path=result_dict['path'],
                                    impl_source=FileReadSource.OH_ACI,
                                )
                        else:  # Error output
                            results.append(result_dict['formatted_output_and_error'])
                    except json.JSONDecodeError:
                        # Handle JSON decoding errors if necessary
                        results.append(
                            f"Invalid JSON in 'openhands-aci' output: {match}"
                        )
                else:
                    for match in matches:
                        try:
                            result_dict = json.loads(match)
                            results.append(result_dict['formatted_output_and_error'])
                        except json.JSONDecodeError:
                            # Handle JSON decoding errors if necessary
                            results.append(
                                f"Invalid JSON in 'openhands-aci' output: {match}"
                            )

                # Combine the results (e.g., join them) or handle them as required
                obs.content = '\n'.join(str(result) for result in results)
            self.last_code = action.code
            self.is_last_code_error = 'Traceback (most recent call last)' in obs.content
            # SLM_Tweak
            # if 'NameError:' in obs.content:
            #     last_line = obs.content.split('\n')[-1]
            #     variable_name = last_line.split("'")[1]
            #     action.code = action.code.replace(variable_name, f"'{variable_name}'")
            #     return await self.run_ipython(action)
            if self.username != 'root':
                if 'Traceback (most recent call last)' in obs.content:
                    obs.content += '\n\n[Hint: Use `search_in_stack_overflow(error_message)` to search for solutions.]'
            # obs.content += f'\n[Jupyter current working directory: {self.bash_session.pwd}]'
            # obs.content += f'\n[Jupyter Python interpreter: {_jupyter_plugin.python_interpreter_path}]'
            return obs
        else:
            raise RuntimeError(
                'JupyterRequirement not found. Unable to run IPython action.'
            )

    def _resolve_path(self, path: str, working_dir: str) -> str:
        filepath = Path(path)
        if not filepath.is_absolute():
            return str(Path(working_dir) / filepath)
        return str(filepath)

    async def read(self, action: FileReadAction) -> Observation:
        assert self.bash_session is not None
        if action.impl_source == FileReadSource.OH_ACI:
            result_str = ''

            return FileReadObservation(
                content=result_str,
                path=action.path,
                impl_source=FileReadSource.OH_ACI,
            )

        # NOTE: the client code is running inside the sandbox,
        # so there's no need to check permission
        working_dir = self.bash_session.cwd
        filepath = self._resolve_path(action.path, working_dir)
        try:
            if filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                with open(filepath, 'rb') as file:
                    image_data = file.read()
                    encoded_image = base64.b64encode(image_data).decode('utf-8')
                    mime_type, _ = mimetypes.guess_type(filepath)
                    if mime_type is None:
                        mime_type = 'image/png'  # default to PNG if mime type cannot be determined
                    encoded_image = f'data:{mime_type};base64,{encoded_image}'

                return FileReadObservation(path=filepath, content=encoded_image)
            elif filepath.lower().endswith('.pdf'):
                with open(filepath, 'rb') as file:
                    pdf_data = file.read()
                    encoded_pdf = base64.b64encode(pdf_data).decode('utf-8')
                    encoded_pdf = f'data:application/pdf;base64,{encoded_pdf}'
                return FileReadObservation(path=filepath, content=encoded_pdf)
            elif filepath.lower().endswith(('.mp4', '.webm', '.ogg')):
                with open(filepath, 'rb') as file:
                    video_data = file.read()
                    encoded_video = base64.b64encode(video_data).decode('utf-8')
                    mime_type, _ = mimetypes.guess_type(filepath)
                    if mime_type is None:
                        mime_type = 'video/mp4'  # default to MP4 if MIME type cannot be determined
                    encoded_video = f'data:{mime_type};base64,{encoded_video}'

                return FileReadObservation(path=filepath, content=encoded_video)
            elif filepath.lower().endswith(('.mp3', '.wav')):
                with open(filepath, 'rb') as file:
                    audio_data = file.read()
                    encoded_audio = base64.b64encode(audio_data).decode('utf-8')
                    mime_type, _ = mimetypes.guess_type(filepath)
                    if mime_type is None:
                        mime_type = 'audio/mpeg'  # default to MP3 if MIME type cannot be determined
                    encoded_audio = f'data:{mime_type};base64,{encoded_audio}'

                return FileReadObservation(path=filepath, content=encoded_audio)

            with open(filepath, 'r', encoding='utf-8') as file:
                lines = read_lines(file.readlines(), action.start, action.end)
        except FileNotFoundError:
            return ErrorObservation(
                f'File not found: {filepath}. Your current working directory is {working_dir}.'
            )
        except UnicodeDecodeError:
            return ErrorObservation(f'File could not be decoded as utf-8: {filepath}.')
        except IsADirectoryError:
            return ErrorObservation(
                f'Path is a directory: {filepath}. You can only read files'
            )

        code_view = ''.join(lines)
        return FileReadObservation(path=filepath, content=code_view)

    async def write(self, action: FileWriteAction) -> Observation:
        assert self.bash_session is not None
        working_dir = self.bash_session.cwd
        filepath = self._resolve_path(action.path, working_dir)

        insert = action.content.split('\n')
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))

        file_exists = os.path.exists(filepath)
        if file_exists:
            file_stat = os.stat(filepath)
        else:
            file_stat = None

        mode = 'w' if not file_exists else 'r+'
        try:
            if not os.path.exists(os.path.dirname(filepath)):
                os.makedirs(os.path.dirname(filepath))

            file_exists = os.path.exists(filepath)
            if file_exists:
                file_stat = os.stat(filepath)
            else:
                file_stat = None

            mode = 'w' if not file_exists else 'r+'
            with open(filepath, mode, encoding='utf-8') as file:
                if mode != 'w':
                    all_lines = file.readlines()
                    new_file = insert_lines(
                        insert, all_lines, action.start, action.end
                    )
                else:
                    new_file = [i + '\n' for i in insert]

                file.seek(0)
                file.writelines(new_file)
                file.truncate()

            # Handle file permissions
            if sys.platform != 'win32':
                if file_exists:
                    assert file_stat is not None
                    # restore the original file permissions if the file already exists
                    os.chmod(filepath, file_stat.st_mode)
                    os.chown(filepath, file_stat.st_uid, file_stat.st_gid)
                else:
                    # set the new file permissions if the file is new
                    os.chmod(filepath, 0o644)
                    os.chown(filepath, self.user_id, self.user_id)

            file.seek(0)
            file.writelines(new_file)
            file.truncate()

        except FileNotFoundError:
            return ErrorObservation(f'File not found: {filepath}')
        except IsADirectoryError:
            return ErrorObservation(
                f'Path is a directory: {filepath}. You can only write to files'
            )
        except UnicodeDecodeError:
            return ErrorObservation(f'File could not be decoded as utf-8: {filepath}')

        # Attempt to handle file permissions
        try:
            if file_exists:
                assert file_stat is not None
                # restore the original file permissions if the file already exists
                os.chmod(filepath, file_stat.st_mode)
                os.chown(filepath, file_stat.st_uid, file_stat.st_gid)
            else:
                # set the new file permissions if the file is new
                os.chmod(filepath, 0o664)
                os.chown(filepath, self.user_id, self.user_id)
        except PermissionError as e:
            return ErrorObservation(
                f'File {filepath} written, but failed to change ownership and permissions: {e}'
            )
        return FileWriteObservation(content='', path=filepath)

    async def edit(self, action: FileEditAction) -> Observation:
        assert action.impl_source == FileEditSource.OH_ACI
        result_str = ''

        return FileEditObservation(
            content=result_str,
            path=action.path,
            old_content=action.old_str,
            new_content=action.new_str,
            impl_source=FileEditSource.OH_ACI,
            diff='',
        )

    async def browse(self, action: BrowseURLAction) -> Observation:
        return await browse(action, self.browser)

    async def browse_interactive(self, action: BrowseInteractiveAction) -> Observation:
        return await browse(action, self.browser)

    def close(self):
        self.memory_monitor.stop_monitoring()
        if self.bash_session is not None:
            self.bash_session.close()
        self.browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=int, help='Port to listen on')
    parser.add_argument('--working-dir', type=str, help='Working directory')
    parser.add_argument('--plugins', type=str, help='Plugins to initialize', nargs='+')
    parser.add_argument(
        '--username', type=str, help='User to run as', default='openhands'
    )
    parser.add_argument('--user-id', type=int, help='User ID to run as', default=1000)
    parser.add_argument(
        '--browsergym-eval-env',
        type=str,
        help='BrowserGym environment used for browser evaluation',
        default=None,
    )
    # example: python client.py 8000 --working-dir /workspace --plugins JupyterRequirement
    args = parser.parse_args()

    plugins_to_load: list[Plugin] = []
    if args.plugins:
        for plugin in args.plugins:
            if plugin not in ALL_PLUGINS:
                raise ValueError(f'Plugin {plugin} not found')
            plugins_to_load.append(ALL_PLUGINS[plugin]())  # type: ignore

    client: ActionExecutor | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global client
        client = ActionExecutor(
            plugins_to_load,
            work_dir=args.working_dir,
            username=args.username,
            user_id=args.user_id,
            browsergym_eval_env=args.browsergym_eval_env,
        )
        await client.ainit()
        yield
        # Clean up & release the resources
        client.close()

    app = FastAPI(lifespan=lifespan)

    # TODO below 3 exception handlers were recommended by Sonnet.
    # Are these something we should keep?
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception('Unhandled exception occurred:')
        return JSONResponse(
            status_code=500,
            content={'detail': 'An unexpected error occurred. Please try again later.'},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.error(f'HTTP exception occurred: {exc.detail}')
        return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        logger.error(f'Validation error occurred: {exc}')
        return JSONResponse(
            status_code=422,
            content={'detail': 'Invalid request parameters', 'errors': exc.errors()},
        )

    @app.middleware('http')
    async def authenticate_requests(request: Request, call_next):
        if request.url.path != '/alive' and request.url.path != '/server_info':
            try:
                verify_api_key(request.headers.get('X-Session-API-Key'))
            except HTTPException as e:
                return e
        response = await call_next(request)
        return response

    @app.get('/server_info')
    async def get_server_info():
        assert client is not None
        current_time = time.time()
        uptime = current_time - client.start_time
        idle_time = current_time - client.last_execution_time

        response = {
            'uptime': uptime,
            'idle_time': idle_time,
            'resources': get_system_stats(),
        }
        logger.info('Server info endpoint response: %s', response)
        return response

    @app.post('/execute_action')
    async def execute_action(action_request: ActionRequest):
        assert client is not None
        try:
            action = event_from_dict(action_request.action)
            if not isinstance(action, Action):
                raise HTTPException(status_code=400, detail='Invalid action type')
            client.last_execution_time = time.time()
            observation = await client.run_action(action)
            return event_to_dict(observation)
        except Exception as e:
            logger.error(f'Error while running /execute_action: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=traceback.format_exc(),
            )

    @app.post('/upload_file')
    async def upload_file(
        file: UploadFile, destination: str = '/', recursive: bool = False
    ):
        assert client is not None

        try:
            # Ensure the destination directory exists
            if not os.path.isabs(destination):
                raise HTTPException(
                    status_code=400, detail='Destination must be an absolute path'
                )

            full_dest_path = destination
            if not os.path.exists(full_dest_path):
                os.makedirs(full_dest_path, exist_ok=True)

            if recursive or file.filename.endswith('.zip'):
                # For recursive uploads, we expect a zip file
                if not file.filename.endswith('.zip'):
                    raise HTTPException(
                        status_code=400, detail='Recursive uploads must be zip files'
                    )

                zip_path = os.path.join(full_dest_path, file.filename)
                with open(zip_path, 'wb') as buffer:
                    shutil.copyfileobj(file.file, buffer)

                # Extract the zip file
                shutil.unpack_archive(zip_path, full_dest_path)
                os.remove(zip_path)  # Remove the zip file after extraction

                logger.debug(
                    f'Uploaded file {file.filename} and extracted to {destination}'
                )
            else:
                # For single file uploads
                file_path = os.path.join(full_dest_path, file.filename)
                with open(file_path, 'wb') as buffer:
                    shutil.copyfileobj(file.file, buffer)
                logger.debug(f'Uploaded file {file.filename} to {destination}')

            return JSONResponse(
                content={
                    'filename': file.filename,
                    'destination': destination,
                    'recursive': recursive,
                },
                status_code=200,
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get('/download_files')
    def download_file(path: str):
        logger.debug('Downloading files')
        try:
            if not os.path.isabs(path):
                raise HTTPException(
                    status_code=400, detail='Path must be an absolute path'
                )

            if not os.path.exists(path):
                raise HTTPException(status_code=404, detail='File not found')

            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                with ZipFile(temp_zip, 'w') as zipf:
                    for root, _, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(
                                file_path, arcname=os.path.relpath(file_path, path)
                            )
                return FileResponse(
                    path=temp_zip.name,
                    media_type='application/zip',
                    filename=f'{os.path.basename(path)}.zip',
                    background=BackgroundTask(lambda: os.unlink(temp_zip.name)),
                )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get('/alive')
    async def alive():
        if client is None or not client.initialized:
            return {'status': 'not initialized'}
        return {'status': 'ok'}

    # ================================
    # VSCode-specific operations
    # ================================

    @app.get('/vscode/connection_token')
    async def get_vscode_connection_token():
        assert client is not None
        if 'vscode' in client.plugins:
            plugin: VSCodePlugin = client.plugins['vscode']  # type: ignore
            return {'token': plugin.vscode_connection_token}
        else:
            return {'token': None}

    # ================================
    # File-specific operations for UI
    # ================================

    @app.post('/list_files')
    async def list_files(request: Request):
        """List files in the specified path.

        This function retrieves a list of files from the agent's runtime file store,
        excluding certain system and hidden files/directories.

        To list files:
        ```sh
        curl http://localhost:3000/api/list-files
        ```

        Args:
            request (Request): The incoming request object.
            path (str, optional): The path to list files from. Defaults to '/'.

        Returns:
            list: A list of file names in the specified path.

        Raises:
            HTTPException: If there's an error listing the files.
        """
        assert client is not None

        # get request as dict
        request_dict = await request.json()
        path = request_dict.get('path', None)

        # Get the full path of the requested directory
        if path is None:
            full_path = client.initial_cwd
        elif os.path.isabs(path):
            full_path = path
        else:
            full_path = os.path.join(client.initial_cwd, path)

        if not os.path.exists(full_path):
            # if user just removed a folder, prevent server error 500 in UI
            return []

        try:
            # Check if the directory exists
            if not os.path.exists(full_path) or not os.path.isdir(full_path):
                return []

            entries = os.listdir(full_path)

            # Separate directories and files
            directories = []
            files = []
            for entry in entries:
                # Remove leading slash and any parent directory components
                entry_relative = entry.lstrip('/').split('/')[-1]

                # Construct the full path by joining the base path with the relative entry path
                full_entry_path = os.path.join(full_path, entry_relative)
                if os.path.exists(full_entry_path):
                    is_dir = os.path.isdir(full_entry_path)
                    if is_dir:
                        # add trailing slash to directories
                        # required by FE to differentiate directories and files
                        entry = entry.rstrip('/') + '/'
                        directories.append(entry)
                    else:
                        files.append(entry)

            # Sort directories and files separately
            directories.sort(key=lambda s: s.lower())
            files.sort(key=lambda s: s.lower())

            # Combine sorted directories and files
            sorted_entries = directories + files
            return sorted_entries

        except Exception as e:
            logger.error(f'Error listing files: {e}')
            return []

    logger.debug(f'Starting action execution API on port {args.port}')
    run(app, host='0.0.0.0', port=args.port)
