import asyncio
import os
import tempfile
import uuid
from typing import Optional
from zipfile import ZipFile

import aiohttp
import docker
import tenacity

from opendevin.core.config import AppConfig
from opendevin.core.logger import opendevin_logger as logger
from opendevin.events import EventStream
from opendevin.events.action import (
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    FileReadAction,
    FileWriteAction,
    IPythonRunCellAction,
)
from opendevin.events.action.action import Action
from opendevin.events.observation import (
    ErrorObservation,
    NullObservation,
    Observation,
)
from opendevin.events.serialization import event_to_dict, observation_from_dict
from opendevin.events.serialization.action import ACTION_TYPE_TO_CLASS
from opendevin.runtime.builder import DockerRuntimeBuilder
from opendevin.runtime.plugins import PluginRequirement
from opendevin.runtime.runtime import Runtime
from opendevin.runtime.utils import find_available_tcp_port
from opendevin.runtime.utils.runtime_build import build_runtime_image


class EventStreamRuntime(Runtime):
    """This runtime will subscribe the event stream.
    When receive an event, it will send the event to od-runtime-client which run inside the docker environment.
    """

    container_name_prefix = 'opendevin-sandbox-'

    def __init__(
        self,
        config: AppConfig,
        event_stream: EventStream,
        sid: str = 'default',
        plugins: list[PluginRequirement] | None = None,
        container_image: str | None = None,
    ):
        super().__init__(
            config, event_stream, sid, plugins
        )  # will initialize the event stream
        self.persist_sandbox = self.config.sandbox.persist_sandbox
        self.fast_boot = self.config.sandbox.fast_boot
        if self.persist_sandbox:
            user = 'od' if self.config.run_as_devin else 'root'
            path = config.workspace_mount_path or ''
            path = ''.join(c if c.isalnum() else '_' for c in path)  # type: ignore
            self.instance_id = f'persisted-{user}-{path}'
            self._port = self.config.sandbox.port
        else:
            self.instance_id = (sid or '') + str(uuid.uuid4())
            self._port = find_available_tcp_port()
        self.api_url = f'http://localhost:{self._port}'
        self.api_url = f'http://{self.config.sandbox.api_hostname}:{self._port}'
        self.session: Optional[aiohttp.ClientSession] = None

        # TODO: We can switch to aiodocker when `get_od_sandbox_image` is updated to use aiodocker
        self.docker_client: docker.DockerClient = self._init_docker_client()
        self.container_image = (
            self.config.sandbox.container_image
            if container_image is None
            else container_image
        )
        self.container_name = self.container_name_prefix + self.instance_id

        self.container = None
        self.action_semaphore = asyncio.Semaphore(1)  # Ensure one action at a time

        self.runtime_builder = DockerRuntimeBuilder(self.docker_client)
        logger.debug(f'EventStreamRuntime `{sid}` config:\n{self.config}')

    async def ainit(self, env_vars: dict[str, str] | None = None):
        if self.config.sandbox.od_runtime_extra_deps:
            logger.info(
                f'Installing extra user-provided dependencies in the runtime image: {self.config.sandbox.od_runtime_extra_deps}'
            )
        try:
            docker.DockerClient().containers.get(self.container_name)
            self.is_initial_session = False
        except docker.errors.NotFound:
            self.is_initial_session = True

        if self.is_initial_session:
            logger.info('Creating new Docker container')
            self.container_image = build_runtime_image(
                self.container_image,
                self.runtime_builder,
                extra_deps=self.config.sandbox.od_runtime_extra_deps,
            )
            self.container = await self._init_container(
                self.sandbox_workspace_dir,
                mount_dir=self.config.workspace_mount_path,
                plugins=self.plugins,
            )
            # MUST call super().ainit() to initialize both default env vars
            # AND the ones in env vars!
            await super().ainit(env_vars)

            logger.info(
                f'Container initialized with plugins: {[plugin.name for plugin in self.plugins]}'
            )
            logger.info(f'Container initialized with env vars: {env_vars}')

        else:
            logger.info('Using existing Docker container')
            self.container = self.docker_client.containers.get(self.container_name)
            await self.start_docker_container()

    @staticmethod
    def _init_docker_client() -> docker.DockerClient:
        try:
            return docker.from_env()
        except Exception as ex:
            logger.error(
                'Launch docker client failed. Please make sure you have installed docker and started the docker daemon.'
            )
            raise ex

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(5),
        wait=tenacity.wait_exponential(multiplier=1, min=4, max=60),
    )
    async def _init_container(
        self,
        sandbox_workspace_dir: str,
        mount_dir: str | None = None,
        plugins: list[PluginRequirement] | None = None,
    ):
        try:
            logger.info(
                f'Starting container with image: {self.container_image} and name: {self.container_name} with port: {self._port}'
            )
            plugin_arg = ''
            if plugins is not None and len(plugins) > 0:
                plugin_arg = (
                    f'--plugins {" ".join([plugin.name for plugin in plugins])} '
                )

            network_mode: str | None = None
            port_mapping: dict[str, int] | None = None
            if self.config.sandbox.use_host_network:
                network_mode = 'host'
                logger.warn(
                    'Using host network mode. If you are using MacOS, please make sure you have the latest version of Docker Desktop and enabled host network feature: https://docs.docker.com/network/drivers/host/#docker-desktop'
                )
            else:
                port_mapping = {f'{self._port}/tcp': self._port}

            if mount_dir is not None:
                volumes = {mount_dir: {'bind': sandbox_workspace_dir, 'mode': 'rw'}}
                # mount sock
                volumes['/var/run/docker.sock'] = {
                    'bind': '/var/run/docker.sock',
                    'mode': 'rw',
                }
                logger.info(f'Mount dir: {sandbox_workspace_dir}')
            else:
                logger.warn(
                    'Mount dir is not set, will not mount the workspace directory to the container.'
                )
                volumes = None

            if self.config.sandbox.browsergym_eval_env is not None:
                browsergym_arg = (
                    f'--browsergym-eval-env {self.config.sandbox.browsergym_eval_env}'
                )
            else:
                browsergym_arg = ''
            container = self.docker_client.containers.run(
                self.container_image,
                command=(
                    f'/opendevin/miniforge3/bin/mamba run --no-capture-output -n base '
                    'PYTHONUNBUFFERED=1 poetry run '
                    f'python -u -m opendevin.runtime.client.client {self._port} '
                    f'--working-dir {sandbox_workspace_dir} '
                    f'{plugin_arg}'
                    f'--username {"opendevin" if self.config.run_as_devin else "root"} '
                    f'--user-id {self.config.sandbox.user_id} '
                    f'{browsergym_arg}'
                ),
                network_mode=network_mode,
                ports=port_mapping,
                working_dir='/opendevin/code/',
                name=self.container_name,
                detach=True,
                environment={'DEBUG': 'true'} if self.config.debug else None,
                volumes=volumes,
            )
            logger.info(f'Container started. Server url: {self.api_url}')
            return container
        except Exception as e:
            logger.error('Failed to start container')
            logger.exception(e)
            await self.close(close_client=False)
            raise e

    async def _ensure_session(self):
        await asyncio.sleep(1)
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    def log_container_logs(self):
        container = self.docker_client.containers.get(self.container_name)
        # get logs
        _logs = container.logs(tail=10).decode('utf-8').split('\n')
        # add indent
        _logs = '\n'.join([f'    |{log}' for log in _logs])
        logger.info(
            '\n'
            + '-' * 30
            + 'Container logs (last 10 lines):'
            + '-' * 30
            + f'\n{_logs}'
            + '\n'
            + '-' * 90
        )

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(10),
        wait=tenacity.wait_exponential(multiplier=2, min=10, max=60),
    )
    async def _wait_until_alive(self):
        logger.info('Reconnecting session')
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.api_url}/alive') as response:
                if response.status != 200:
                    msg = f'Action execution API is not alive. Response: {response}'
                    logger.error(msg)
                    self.log_container_logs()
                    raise RuntimeError(msg)

    @property
    def sandbox_workspace_dir(self):
        return self.config.workspace_mount_path_in_sandbox

    async def start_docker_container(self):
        try:
            container = self.docker_client.containers.get(self.container_name)
            logger.info('Container status: %s', container.status)
            if container.status != 'running':
                container.start()
                logger.info('Container started')
            elapsed = 0
            while container.status != 'running':
                await asyncio.sleep(1)
                elapsed += 1
                if elapsed > self.config.sandbox.timeout:
                    break
                container = self.docker_client.containers.get(self.container_name)
        except Exception:
            logger.exception('Failed to start container')

    async def close(self, close_client: bool = True):
        if self.session is not None and not self.session.closed:
            await self.session.close()

        containers = self.docker_client.containers.list(all=True)
        for container in containers:
            try:
                # only remove the container it created
                # otherwise all other containers with the same prefix will be removed
                # which will mess up with parallel evaluation
                if container.name.startswith(self.container_name):
                    logs = container.logs(tail=1000).decode('utf-8')
                    logger.debug(
                        f'==== Container logs ====\n{logs}\n==== End of container logs ===='
                    )
                    if self.persist_sandbox:
                        if not self.fast_boot:
                            container.stop()
                    else:
                        container.remove(force=True)
            except docker.errors.NotFound:
                pass
        if close_client:
            self.docker_client.close()

    async def run_action(self, action: Action) -> Observation:
        # set timeout to default if not set
        if action.timeout is None:
            action.timeout = self.config.sandbox.timeout

        async with self.action_semaphore:
            if not action.runnable:
                return NullObservation('')
            action_type = action.action  # type: ignore[attr-defined]
            if action_type not in ACTION_TYPE_TO_CLASS:
                return ErrorObservation(f'Action {action_type} does not exist.')
            if not hasattr(self, action_type):
                return ErrorObservation(
                    f'Action {action_type} is not supported in the current runtime.'
                )

            logger.info('Awaiting session')
            session = await self._ensure_session()
            await self._wait_until_alive()

            assert action.timeout is not None

            try:
                logger.info(f'Executing action {action}')
                async with session.post(
                    f'{self.api_url}/execute_action',
                    json={'action': event_to_dict(action)},
                    timeout=action.timeout,
                ) as response:
                    if response.status == 200:
                        output = await response.json()
                        obs = observation_from_dict(output)
                        obs._cause = action.id  # type: ignore[attr-defined]
                        return obs
                    else:
                        error_message = await response.text()
                        logger.error(f'Error from server: {error_message}')
                        obs = ErrorObservation(
                            f'Command execution failed: {error_message}'
                        )
            except asyncio.TimeoutError:
                logger.error('No response received within the timeout period.')
                obs = ErrorObservation('Command execution timed out')
            except Exception as e:
                logger.error(f'Error during command execution: {e}')
                obs = ErrorObservation(f'Command execution failed: {str(e)}')
            return obs

    async def run(self, action: CmdRunAction) -> Observation:
        return await self.run_action(action)

    async def run_ipython(self, action: IPythonRunCellAction) -> Observation:
        return await self.run_action(action)

    async def read(self, action: FileReadAction) -> Observation:
        return await self.run_action(action)

    async def write(self, action: FileWriteAction) -> Observation:
        return await self.run_action(action)

    async def browse(self, action: BrowseURLAction) -> Observation:
        return await self.run_action(action)

    async def browse_interactive(self, action: BrowseInteractiveAction) -> Observation:
        return await self.run_action(action)

    # ====================================================================
    # Implement these methods (for file operations) in the subclass
    # ====================================================================

    async def copy_to(
        self, host_src: str, sandbox_dest: str, recursive: bool = False
    ) -> None:
        if not os.path.exists(host_src):
            raise FileNotFoundError(f'Source file {host_src} does not exist')

        session = await self._ensure_session()
        await self._wait_until_alive()
        try:
            if recursive:
                # For recursive copy, create a zip file
                with tempfile.NamedTemporaryFile(
                    suffix='.zip', delete=False
                ) as temp_zip:
                    temp_zip_path = temp_zip.name

                with ZipFile(temp_zip_path, 'w') as zipf:
                    for root, _, files in os.walk(host_src):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(
                                file_path, os.path.dirname(host_src)
                            )
                            zipf.write(file_path, arcname)

                upload_data = {'file': open(temp_zip_path, 'rb')}
            else:
                # For single file copy
                upload_data = {'file': open(host_src, 'rb')}

            params = {'destination': sandbox_dest, 'recursive': str(recursive).lower()}

            async with session.post(
                f'{self.api_url}/upload_file', data=upload_data, params=params
            ) as response:
                if response.status == 200:
                    return
                else:
                    error_message = await response.text()
                    raise Exception(f'Copy operation failed: {error_message}')

        except asyncio.TimeoutError:
            raise TimeoutError('Copy operation timed out')
        except Exception as e:
            raise RuntimeError(f'Copy operation failed: {str(e)}')
        finally:
            if recursive:
                os.unlink(temp_zip_path)
            logger.info(f'Copy completed: host:{host_src} -> runtime:{sandbox_dest}')

    async def list_files(self, path: str | None = None) -> list[str]:
        """List files in the sandbox.

        If path is None, list files in the sandbox's initial working directory (e.g., /workspace).
        """
        session = await self._ensure_session()
        await self._wait_until_alive()
        try:
            data = {}
            if path is not None:
                data['path'] = path

            async with session.post(
                f'{self.api_url}/list_files', json=data
            ) as response:
                if response.status == 200:
                    response_json = await response.json()
                    assert isinstance(response_json, list)
                    return response_json
                else:
                    error_message = await response.text()
                    raise Exception(f'List files operation failed: {error_message}')
        except asyncio.TimeoutError:
            raise TimeoutError('List files operation timed out')
        except Exception as e:
            raise RuntimeError(f'List files operation failed: {str(e)}')
