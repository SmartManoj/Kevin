from typing import Callable

from openhands.core.config import AppConfig
from openhands.events.action import (
    FileReadAction,
    FileWriteAction,
)
from openhands.events.action.browse import BrowseInteractiveAction, BrowseURLAction
from openhands.events.action.commands import CmdRunAction, IPythonRunCellAction
from openhands.events.action.mcp import MCPAction
from openhands.events.observation import (
    ErrorObservation,
    FileReadObservation,
    FileWriteObservation,
    Observation,
)
from openhands.events.observation.commands import CmdOutputObservation
from openhands.events.stream import EventStream
from openhands.runtime.base import Runtime
from openhands.runtime.impl.e2b.filestore import E2BFileStore
from openhands.runtime.impl.e2b.sandbox import E2BSandbox
from openhands.runtime.plugins import PluginRequirement
from openhands.runtime.utils.files import insert_lines, read_lines


class E2BRuntime(Runtime):
    def __init__(
        self,
        config: AppConfig,
        event_stream: EventStream,
        sid: str = 'default',
        plugins: list[PluginRequirement] | None = None,
        sandbox: E2BSandbox | None = None,
        status_callback: Callable | None = None,
        headless_mode: bool = True,
        attach_to_existing: bool = False,
        env_vars: dict[str, str] | None = None,
        user_id: str | None = None,
    ):
        super().__init__(
            config,
            event_stream,
            sid,
            plugins,
            status_callback=status_callback,
            headless_mode=headless_mode,
            attach_to_existing=attach_to_existing,
            env_vars=env_vars,
            user_id=user_id,
        )
        if sandbox is None:
            self.sandbox = E2BSandbox(config.sandbox, config.e2b_api_key)
        if not isinstance(self.sandbox, E2BSandbox):
            raise ValueError('E2BRuntime requires an E2BSandbox')
        self.file_store = E2BFileStore(self.sandbox.filesystem)

    def read(self, action: FileReadAction) -> Observation:
        try:
            content = self.file_store.read(action.path)
            lines = read_lines(content.split('\n'), action.start, action.end)
            code_view = ''.join(lines)
            return FileReadObservation(code_view, path=action.path)
        except FileNotFoundError as e:
            return ErrorObservation(f"File not found: {action.path}")
        except Exception as e:
            return ErrorObservation(f"Error reading file: {action.path}")

    def write(self, action: FileWriteAction) -> Observation:
        if action.start == 0 and action.end == -1:
            self.file_store.write(action.path, action.content)
            return FileWriteObservation(content='', path=action.path)
        files = self.file_store.list(action.path)
        if action.path in files:
            all_lines = self.file_store.read(action.path).split('\n')
            new_file = insert_lines(
                action.content.split('\n'), all_lines, action.start, action.end
            )
            self.file_store.write(action.path, ''.join(new_file))
            return FileWriteObservation('', path=action.path)
        else:
            # FIXME: we should create a new file here
            return ErrorObservation(f'File not found: {action.path}')

    def browse(self, action: BrowseURLAction) -> Observation:
        pass

    def browse_interactive(self, action: BrowseInteractiveAction) -> Observation:
        pass

    async def call_tool_mcp(self, action: MCPAction) -> Observation:
        pass

    async def connect(self):
        pass

    async def copy_from(self, path: str) -> Observation:
        return NotImplementedError

    async def copy_to(self, host_src: str, sandbox_dest: str, recursive: bool = False) -> None:
        self.sandbox.copy_to(host_src, sandbox_dest, recursive)

    def list_files(self, path: str | None = None) -> list[str]:
        return self.file_store.list(path)
    
    def run(self, action: CmdRunAction) -> CmdOutputObservation | ErrorObservation:
        exit_code, output = self.sandbox.execute(action.command)
        if exit_code == 0:
            return CmdOutputObservation(output, exit_code, action.command)
        else:
            return ErrorObservation(output)

    def run_ipython(self, action: IPythonRunCellAction) -> Observation:
        return NotImplementedError
