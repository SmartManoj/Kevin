import os
import re
import time
import traceback
import uuid
from enum import Enum

import bashlex
import pexpect

from openhands.core.logger import openhands_logger as logger
from openhands.events.action import CmdRunAction
from openhands.events.observation import ErrorObservation
from openhands.events.observation.commands import (
    CMD_OUTPUT_PS1_END,
    CmdOutputMetadata,
    CmdOutputObservation,
)
from openhands.utils.shutdown_listener import should_continue


def split_bash_commands(commands):
    if not commands.strip():
        return ['']
    try:
        parsed = bashlex.parse(commands)
    except (bashlex.errors.ParsingError, NotImplementedError):
        logger.debug(
            f'Failed to parse bash commands\n'
            f'[input]: {commands}\n'
            f'[warning]: {traceback.format_exc()}\n'
            f'The original command will be returned as is.'
        )
        # If parsing fails, return the original commands
        return [commands]

    result: list[str] = []
    last_end = 0

    for node in parsed:
        start, end = node.pos

        # Include any text between the last command and this one
        if start > last_end:
            between = commands[last_end:start]
            logger.debug(f'BASH PARSING between: {between}')
            if result:
                result[-1] += between.rstrip()
            elif between.strip():
                # THIS SHOULD NOT HAPPEN
                result.append(between.rstrip())

        # Extract the command, preserving original formatting
        command = commands[start:end].rstrip()
        logger.debug(f'BASH PARSING command: {command}')
        result.append(command)

        last_end = end

    # Add any remaining text after the last command to the last command
    remaining = commands[last_end:].rstrip()
    logger.debug(f'BASH PARSING: {remaining = }')
    if last_end < len(commands) and result:
        result[-1] += remaining
        logger.debug(f'BASH PARSING result[-1] += remaining: {result[-1]}')
    elif last_end < len(commands):
        if remaining:
            result.append(remaining)
            logger.debug(f'BASH PARSING result.append(remaining): {result[-1]}')
    return result


def escape_bash_special_chars(command: str) -> str:
    if command.strip() == '':
        return ''

    try:
        parts = []
        last_pos = 0

        def visit_node(node):
            nonlocal last_pos
            if (
                node.kind == 'redirect'
                and hasattr(node, 'heredoc')
                and node.heredoc is not None
            ):
                between = command[last_pos : node.pos[0]]
                parts.append(between)
                parts.append(command[node.pos[0] : node.heredoc.pos[0]])
                parts.append(command[node.heredoc.pos[0] : node.heredoc.pos[1]])
                last_pos = node.pos[1]
                return

            if node.kind == 'word':
                between = command[last_pos : node.pos[0]]
                word_text = command[node.pos[0] : node.pos[1]]
                between = re.sub(r'\\([;&|><])', r'\\\\\1', between)
                parts.append(between)

                if (
                    (word_text.startswith('"') and word_text.endswith('"'))
                    or (word_text.startswith("'") and word_text.endswith("'"))
                    or (word_text.startswith('$(') and word_text.endswith(')'))
                    or (word_text.startswith('`') and word_text.endswith('`'))
                ):
                    parts.append(word_text)
                else:
                    word_text = re.sub(r'\\([;&|><])', r'\\\\\1', word_text)
                    parts.append(word_text)
                last_pos = node.pos[1]
                return

            if hasattr(node, 'parts'):
                for part in node.parts:
                    visit_node(part)

        nodes = list(bashlex.parse(command))
        for node in nodes:
            between = command[last_pos : node.pos[0]]
            between = re.sub(r'\\([;&|><])', r'\\\\\1', between)
            parts.append(between)
            last_pos = node.pos[0]
            visit_node(node)

        remaining = command[last_pos:]
        parts.append(remaining)
        return ''.join(parts)
    except (bashlex.errors.ParsingError, NotImplementedError):
        logger.debug(
            f'Failed to parse bash commands for special characters escape\n'
            f'[input]: {command}\n'
            f'[warning]: {traceback.format_exc()}\n'
            f'The original command will be returned as is.'
        )
        return command


class BashCommandStatus(Enum):
    CONTINUE = 'continue'
    COMPLETED = 'completed'
    NO_CHANGE_TIMEOUT = 'no_change_timeout'
    HARD_TIMEOUT = 'hard_timeout'


def _remove_command_prefix(command_output: str, command: str) -> str:
    return command_output.lstrip().removeprefix(command.lstrip()).lstrip()


class BashSession:
    POLL_INTERVAL = 0.5
    HISTORY_LIMIT = 10_000
    PS1 = r'[PEXPECT_BEGIN]\u@\h:\w\n[PEXPECT_END]'
    bash_expect_regex = r'\[PEXPECT_BEGIN\]\s*(.*?)\s*([a-z0-9_-]*)@([a-zA-Z0-9.-]*):(.+)\s*\[PEXPECT_END\]'

    def __init__(
        self,
        work_dir: str,
        username: str | None = None,
        no_change_timeout_seconds: int = 10,
    ):
        self.NO_CHANGE_TIMEOUT_SECONDS = no_change_timeout_seconds
        self.work_dir = work_dir
        self.username = username
        self._initialized = False
        self.last_command = ''
        self.child = None

    def initialize(self):
        """Initialize the Bash session using pexpect."""
        self.child = pexpect.spawn('/bin/bash', encoding='utf-8', timeout=30)
        self.child.expect(r'\$')  # Wait for the shell prompt

        # Set the working directory
        self.child.sendline(f'cd {self.work_dir}')
        self.child.expect(r'\$')

        logger.info(f'PS1: {self.PS1}')
        # Configure bash to use a simple PS1 prompt
        self.child.sendline(f'export PS1="{self.PS1}"')
        self.child.expect(self.bash_expect_regex)


        logger.debug(f'Bash session initialized with work dir: {self.work_dir}')

        # Maintain the current working directory
        self._cwd = os.path.abspath(self.work_dir)
        self._initialized = True

    def __del__(self):
        """Ensure the session is closed when the object is destroyed."""
        self.close()

    def close(self):
        """Close the Bash session."""
        if self.child and self.child.isalive():
            self.child.close()
        self._initialized = False

    @property
    def cwd(self):
        return self._cwd
    def execute(self, action: CmdRunAction) -> CmdOutputObservation | ErrorObservation:
        """Execute a command in the Bash session."""
        if not self._initialized:
            raise RuntimeError('Bash session is not initialized')

        command = action.command.strip()
        is_input: bool = action.is_input
        output = None
        if command == self.last_command and command in ['ls -l', 'ls -la']:
            output = "[Why are you executing the same command twice? What's wrong with you? Please focus 🙏]"
        elif command.startswith('cd'):
            path = command[3:].strip()
            if self.cwd == path:
                output = '[You are already in this directory.]'
        elif self.username == 'root':
            if command.startswith('git blame'):
                output = "[Don't use git commands. Just directly give the solution.]"
            elif 'pip install' in command and os.getenv('NO_PIP_INSTALL') == '1':
                output = '[Use the current packages only.]'

            elif (
                '/tmp/test_task.py' in command
                and 'cat' not in command
                and 'python3' not in command
                and 'pytest' not in command
            ):
                output = "[The content in this file is absolutely correct. Also, you can't modify this test file. You must pass this test case. You should correct the codebase instead.]"
            elif command.startswith('pytest') and '.py' not in command:
                output = '[Please run specific test cases instead of running all test cases.]'
        if output:
            return CmdOutputObservation(
                content=output,
                command='',
                metadata=CmdOutputMetadata(exit_code=0),
            )

        # Send the command to the shell
        self.child.sendline(command)
        self.child.expect(self.bash_expect_regex)  # Wait for the shell prompt

        # Capture the output
        output = self.child.before[len(command):].strip()
        return CmdOutputObservation(
            content=output,
            command=command,
            metadata=CmdOutputMetadata(exit_code=0),
        )

    def parse_pip_output(self, code, output) -> str:
        package_names = code.split(' ', 2)[-1]
        parsed_output = output
        if 'Successfully installed' in output:
            parsed_output = '[Package installed successfully]'
        else:
            package_names = package_names.split()
            if all(
                f'Requirement already satisfied: {package_name}' in output
                for package_name in package_names
            ):
                plural = 's' if len(package_names) > 1 else ''
                parsed_output = f'[Package{plural} already installed]'

        return parsed_output
    

if __name__ == '__main__':
    bash_session = BashSession(work_dir='workspace')
    bash_session.initialize()
    print(bash_session.execute(CmdRunAction(command='ls -l')))
