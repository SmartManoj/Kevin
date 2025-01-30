import os
import re

from openhands.controller.action_parser import (
    ActionParser,
    ResponseParser,
)
from openhands.core.exceptions import LLMMalformedActionError
from openhands.core.logger import openhands_logger as logger
from openhands.events.action import (
    Action,
    AgentDelegateAction,
    AgentFinishAction,
    AgentSummarizeAction,
    CmdRunAction,
    FileEditAction,
    IPythonRunCellAction,
    MessageAction,
)
from openhands.events.action.browse import BrowseURLAction


class CodeActResponseParser(ResponseParser):
    """Parser action:
    - CmdRunAction(command) - bash command to run
    - FileEditAction(path, content) - edit a file
    - IPythonRunCellAction(code) - IPython code to run
    - AgentDelegateAction(agent, inputs) - delegate action for (sub)task
    - MessageAction(content) - Message action to run (e.g. ask for clarification)
    - AgentFinishAction() - end the interaction
    """

    def __init__(self):
        # Need pay attention to the item order in self.action_parsers
        super().__init__()
        self.action_parsers = [
            CodeActActionParserFileEdit(),
            CodeActActionParserIPythonRunCell(),
            CodeActActionParserCmdRun(),
            CodeActActionParserAgentDelegate(),
            CodeActActionParserFinish(),
        ]
        self.default_parser = CodeActActionParserMessage()

    def parse(self, response) -> Action:
        if isinstance(response, AgentSummarizeAction):
            return response
        action_str = self.parse_response(response)
        return self.parse_action(action_str)

    def parse_response(self, response) -> str:
        # action = response.choices[0].message.content
        action = response['choices'][0]['message']['content']
        if action is None:
            return ''

        action = re.sub(r"<think>.*?</think>", "", action, flags=re.DOTALL)
        
        action = action.replace(r'\_', '_')  # Mistral Large gives \_ instead of _
        three_backticks = '```'
        if action.count(three_backticks) % 2 == 1 and '<execute_' not in action:
            action += three_backticks
        for lang in ['bash', 'ipython', 'browse']:
            # special handling for DeepSeek: it has stop-word bug and returns </execute_ipython instead of </execute_ipython>
            if f'</execute_{lang}' in action and f'</execute_{lang}>' not in action:
                action = action.replace(f'</execute_{lang}', f'</execute_{lang}>')

            open_tag = f'<execute_{lang}>(?!`)'  # not followed by a backtick
            close_tag = f'</execute_{lang}>'
            if re.search(open_tag, action) and close_tag not in action:
                action += close_tag

        # special handling for DeepSeek: it has stop-word bug and returns </execute_ipython instead of </execute_ipython>
        if '</file_edit' in action and '</file_edit>' not in action:
            action = action.replace('</file_edit', '</file_edit>')

        if '<file_edit' in action and '</file_edit>' not in action:
            action += '</file_edit>'
        return action

    def parse_action(self, action_str: str) -> Action:
        for action_parser in self.action_parsers:
            if action_parser.check_condition(action_str):
                return action_parser.parse(action_str)
        return self.default_parser.parse(action_str)

    @classmethod
    def action_to_str(self, action: Action) -> str:
        if isinstance(action, CmdRunAction):
            return (
                f'{action.thought}\n<execute_bash>\n{action.command}\n</execute_bash>'
            )
        elif isinstance(action, IPythonRunCellAction):
            return f'{action.thought}\n<execute_ipython>\n{action.code}\n</execute_ipython>'
        elif isinstance(action, AgentDelegateAction):
            return f'{action.thought}\n<execute_browse>\n{action.inputs["task"]}\n</execute_browse>'
        elif isinstance(action, FileEditAction):
            return f'{action.thought}\n<file_edit path={action.path}>\n{action.content}\n</file_edit>'
        elif isinstance(action, MessageAction):
            return action.content
        elif isinstance(action, BrowseURLAction):
            return f'Opening {action.url} in browser manually'
        elif isinstance(action, AgentSummarizeAction):
            return (
                'Summary of all Action and Observations till now. \n'
                f'Action: {action.summarized_actions}\n'
                f'Observation: {action.summarized_observations}'
            )
        elif isinstance(action, AgentFinishAction) and action.source == 'agent':
            # Gemini: Unable to submit request because it has an empty text parameter
            return action.thought or 'The task is done.'

        return ''


class CodeActActionParserFinish(ActionParser):
    """Parser action:
    - AgentFinishAction() - end the interaction
    """

    def __init__(
        self,
    ):
        self.finish_command = None
        self.is_finish2 = False

    def check_condition(self, action_str: str) -> bool:
        self.finish_command = re.search(r'<finish>.*</finish>', action_str, re.DOTALL)
        if self.finish_command is None:
            self.finish_command = re.search(r'<end>.*</end>', action_str, re.DOTALL)
            if self.finish_command is not None:
                self.is_finish2 = True
        return self.finish_command is not None

    def parse(self, action_str: str) -> Action:
        assert (
            self.finish_command is not None
        ), 'self.finish_command should not be None when parse is called'
        thought = action_str.replace(self.finish_command.group(0), '').strip()
        os.environ['finish_thought'] = thought
        if not self.is_finish2 and os.getenv('TEST_TASK') == '1':
            test_tool = os.getenv('TEST_TOOL', 'python3')
            return CmdRunAction(f'{test_tool} /tmp/test_task.py', thought='')
        return AgentFinishAction(thought=thought)


class CodeActActionParserCmdRun(ActionParser):
    """Parser action:
    - CmdRunAction(command) - bash command to run
    - AgentFinishAction() - end the interaction
    """

    def __init__(
        self,
    ):
        self.bash_command = None

    def check_condition(self, action_str: str) -> bool:
        self.bash_command = re.search(
            r'<execute_bash>(.*\S.*)</execute_bash>', action_str, re.DOTALL
        )
        if self.bash_command is None and '<execute_' not in action_str:
            # Gemini flash not providing the tag and returns as code wrap in backticks
            self.bash_command = re.search(
                r'^```bash(.*)```', action_str, re.DOTALL | re.MULTILINE
            )
        return self.bash_command is not None

    def parse(self, action_str: str) -> Action:
        assert (
            self.bash_command is not None
        ), 'self.bash_command should not be None when parse is called'
        thought = action_str.replace(self.bash_command.group(0), '').strip()
        # a command was found
        command = self.bash_command.group(1).strip()
        if command.strip() == 'exit':
            return AgentFinishAction(thought=thought)
        return CmdRunAction(command=command, thought=thought)


class CodeActActionParserIPythonRunCell(ActionParser):
    """Parser action:
    - IPythonRunCellAction(code) - IPython code to run
    """

    def __init__(
        self,
    ):
        self.python_code = None

    def check_condition(self, action_str: str) -> bool:
        self.python_code = re.search(
            r'<execute_ipython>(.*\S.*)</execute_ipython>', action_str, re.DOTALL
        )
        if self.python_code is None and '<execute_' not in action_str:
            # For Gemini: tool_code is not a valid tag and returns as code wrap in backticks
            self.python_code = re.search(
                r'^```(?:python|tool_code)(.*)```', action_str, re.DOTALL | re.MULTILINE
            )
        return self.python_code is not None

    def parse(self, action_str: str) -> Action:
        assert (
            self.python_code is not None
        ), 'self.python_code should not be None when parse is called'
        code = self.python_code.group(1).strip()
        three_single_quotes = "'''"
        three_backticks = '```'
        # for gemini-flash
        if three_backticks in code:
            if code.count(three_single_quotes) % 2 == 1:
                code = code.replace(three_backticks, three_single_quotes).strip()
            else:
                code = code.replace(three_backticks, '').strip()

        thought = action_str.replace(self.python_code.group(0), '').strip()
        thought = re.sub(r'```(python|tool_code)\s*(```)?', '', thought)

        # escape "\n"
        triple_single_quotes = "'''"
        triple_double_quotes = '"""'
        if triple_single_quotes not in code and triple_double_quotes not in code:
            code = code.replace('"\n"', '"\\n"')
            code = code.replace("'\n'", "'\\n'")

        def convert_to_raw_string(input_code: str) -> str:
            # Regex pattern to find triple quotes and add 'r' before them if not already present
            pattern1 = r"r?('''.*?\\n.*?''')"
            pattern2 = r'r?"""(.*?\\n.*?)"""'

            # replace only if \n inside the string
            output_code = re.sub(pattern1, r'r\1', input_code, flags=re.DOTALL)
            output_code = re.sub(pattern2, r"r'''\1'''", output_code, flags=re.DOTALL)

            return output_code

        code = convert_to_raw_string(code)
        return IPythonRunCellAction(
            code=code,
            thought=thought,
        )


class CodeActActionParserAgentDelegate(ActionParser):
    """Parser action:
    - AgentDelegateAction(agent, inputs) - delegate action for (sub)task
    """

    def __init__(
        self,
    ):
        self.agent_delegate = None

    def check_condition(self, action_str: str) -> bool:
        self.agent_delegate = re.search(
            r'<execute_browse>(.*)</execute_browse>', action_str, re.DOTALL
        )
        return self.agent_delegate is not None

    def parse(self, action_str: str) -> Action:
        assert (
            self.agent_delegate is not None
        ), 'self.agent_delegate should not be None when parse is called'
        thought = action_str.replace(self.agent_delegate.group(0), '').strip()
        browse_actions = self.agent_delegate.group(1).strip()
        thought = (
            f'{thought}\nI should start with: {browse_actions}'
            if thought
            else f'I should start with: {browse_actions}'
        )

        return AgentDelegateAction(
            agent='BrowsingAgent', thought=thought, inputs={'task': browse_actions}
        )


class CodeActActionParserMessage(ActionParser):
    """Parser action:
    - MessageAction(content) - Message action to run (e.g. ask for clarification)
    """

    def __init__(
        self,
    ):
        pass

    def check_condition(self, action_str: str) -> bool:
        # We assume the LLM is GOOD enough that when it returns pure natural language
        # it wants to talk to the user
        return True

    def parse(self, action_str: str) -> Action:
        return MessageAction(content=action_str, wait_for_response=True)


class CodeActActionParserFileEdit(ActionParser):
    """Parser action:
    - FileEditAction(path, content) - edit a file
    """

    def __init__(self):
        self.file_edit_match: re.Match | None = None

    def check_condition(self, action_str: str) -> bool:
        if '<file_edit' not in action_str:
            return False

        # Updated regex to make start and end optional
        self.file_edit_match = re.search(
            r'<file_edit\s+path=(["\']?)(.*?)\1(?:\s+start=(["\']?)(.*?)\3)?(?:\s+end=(["\']?)(.*?)\5)?\s*>(.*?)</file_edit>',
            action_str,
            re.DOTALL,
        )

        if self.file_edit_match is None:
            logger.error(
                f'FileEditAction detected but the format is incorrect. Unable to match for <file_edit> in:\n{"-" * 80}\n{action_str}\n{"-" * 80}'
            )
            raise LLMMalformedActionError(
                'FileEditAction detected but the format is incorrect. Usage:\n'
                '<file_edit path="[path]" start=[start_line] end=[end_line]>\n'
                '[content_to_edit]\n'
                '</file_edit>\n'
            )

        path = self.file_edit_match.group(2)
        start = self.file_edit_match.group(4)
        end = self.file_edit_match.group(6)

        if not path:
            raise LLMMalformedActionError(
                'FileEditAction detected but no `path` specified. You should specify the path of the file to edit.'
            )

        if start:
            try:
                int(start)
            except ValueError:
                raise LLMMalformedActionError(
                    f'FileEditAction detected but `start` is not a valid integer: {start}'
                )

        if end:
            try:
                int(end)
            except ValueError:
                raise LLMMalformedActionError(
                    f'FileEditAction detected but `end` is not a valid integer: {end}'
                )

        return True

    def parse(self, action_str: str) -> Action:
        assert (
            self.file_edit_match is not None
        ), 'self.file_edit_match should not be None when parse is called'

        file_path = self.file_edit_match.group(2).strip()
        start_line = (
            int(self.file_edit_match.group(4))
            if self.file_edit_match.group(4)
            else None
        )
        end_line = (
            int(self.file_edit_match.group(6))
            if self.file_edit_match.group(6)
            else None
        )
        content = self.file_edit_match.group(7)
        thought = action_str.replace(self.file_edit_match.group(0), '').strip()

        action = FileEditAction(path=file_path, content=content, thought=thought)
        if start_line is not None:
            action.start = start_line
        if end_line is not None:
            action.end = end_line
        return action


if __name__ == '__main__':
    log = 'logs/llm/default/006_response.log'
    with open(log, 'r') as f:
        response = f.read()
    response = {'choices': [{'message': {'content': response}}]}  # type: ignore
    action_parser = CodeActResponseParser()
    action = action_parser.parse(response)
    print(action)
