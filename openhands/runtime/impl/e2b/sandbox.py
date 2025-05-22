import copy
import os
import tarfile
from glob import glob

from e2b import Sandbox
from e2b.sandbox.commands.command_handle import CommandExitException

from openhands.core.config import SandboxConfig
from openhands.core.logger import openhands_logger as logger


class E2BSandbox:
    closed = False
    _cwd: str = '/home/user'
    _env: dict[str, str] = {}
    is_initial_session: bool = True

    def __init__(
        self,
        config: SandboxConfig,
        e2b_api_key: str,
    ):
        self.config = copy.deepcopy(config)
        self.initialize_plugins: bool = config.initialize_plugins
        self.sandbox = Sandbox(
            api_key=e2b_api_key or self.config.api_key,
        )
        logger.debug(f'Started E2B sandbox with ID "{self.sandbox.sandbox_id}"')

    @property
    def filesystem(self):
        return self.sandbox._filesystem

    def _archive(self, host_src: str, recursive: bool = False):
        if recursive:
            assert os.path.isdir(host_src), (
                'Source must be a directory when recursive is True'
            )
            files = glob(host_src + '/**/*', recursive=True)
            srcname = os.path.basename(host_src)
            tar_filename = os.path.join(os.path.dirname(host_src), srcname + '.tar')
            with tarfile.open(tar_filename, mode='w') as tar:
                for file in files:
                    tar.add(
                        file, arcname=os.path.relpath(file, os.path.dirname(host_src))
                    )
        else:
            assert os.path.isfile(host_src), (
                'Source must be a file when recursive is False'
            )
            srcname = os.path.basename(host_src)
            tar_filename = os.path.join(os.path.dirname(host_src), srcname + '.tar')
            with tarfile.open(tar_filename, mode='w') as tar:
                tar.add(host_src, arcname=srcname)
        return tar_filename

    def execute(self, cmd: str, timeout: int | None = None) -> tuple[int, str]:
        timeout = timeout if timeout is not None else self.config.timeout
        try:
            process = self.sandbox.commands.run(cmd, envs=self._env, timeout=timeout)
            output = process.stdout
            exit_code = process.exit_code
        except CommandExitException as e:
            output = e.stdout
            exit_code = e.exit_code
        return exit_code, output

    def copy_to(self, host_src: str, sandbox_dest: str, recursive: bool = False):
        """Copies a local file or directory to the sandbox."""
        tar_filename = self._archive(host_src, recursive)

        # Prepend the sandbox destination with our sandbox cwd
        sandbox_dest = os.path.join(self._cwd, sandbox_dest.removeprefix('/'))

        with open(tar_filename, 'rb') as tar_file:
            # Upload the archive to /home/user (default destination that always exists)
            uploaded_path = self.sandbox.upload_file(tar_file)

            # Check if sandbox_dest exists. If not, create it.
            process = self.sandbox.process.start_and_wait(f'test -d {sandbox_dest}')
            if process.exit_code != 0:
                self.sandbox.filesystem.make_dir(sandbox_dest)

            # Extract the archive into the destination and delete the archive
            process = self.sandbox.process.start_and_wait(
                f'sudo tar -xf {uploaded_path} -C {sandbox_dest} && sudo rm {uploaded_path}'
            )
            if process.exit_code != 0:
                raise Exception(
                    f'Failed to extract {uploaded_path} to {sandbox_dest}: {process.stderr}'
                )

        # Delete the local archive
        os.remove(tar_filename)

    def close(self):
        self.sandbox.close()

    def get_working_directory(self):
        return self.sandbox.cwd
