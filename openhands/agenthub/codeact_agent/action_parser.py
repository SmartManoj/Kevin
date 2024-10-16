import os
import re

from openhands.controller.action_parser import ActionParser, ResponseParser
from openhands.events.action import (
    Action,
    AgentDelegateAction,
    AgentFinishAction,
    AgentSummarizeAction,
    CmdRunAction,
    IPythonRunCellAction,
    MessageAction,
)


class CodeActResponseParser(ResponseParser):
    """Parser action:
    - CmdRunAction(command) - bash command to run
    - IPythonRunCellAction(code) - IPython code to run
    - AgentDelegateAction(agent, inputs) - delegate action for (sub)task
    - MessageAction(content) - Message action to run (e.g. ask for clarification)
    - AgentFinishAction() - end the interaction
    """

    def __init__(self):
        # Need pay attention to the item order in self.action_parsers
        super().__init__()
        self.action_parsers = [
            CodeActActionParserCmdRun(),
            CodeActActionParserIPythonRunCell(),
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
        for lang in ['bash', 'ipython', 'browse']:
            # special handling for DeepSeek: it has stop-word bug and returns </execute_ipython instead of </execute_ipython>
            if f'</execute_{lang}' in action and f'</execute_{lang}>' not in action:
                action = action.replace(f'</execute_{lang}', f'</execute_{lang}>')

            if f'<execute_{lang}>' in action and f'</execute_{lang}>' not in action:
                action += f'</execute_{lang}>'
        return action

    def parse_action(self, action_str: str) -> Action:
        for action_parser in self.action_parsers:
            if action_parser.check_condition(action_str):
                return action_parser.parse(action_str)
        return self.default_parser.parse(action_str)


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
        if not self.is_finish2 and os.getenv('SWE_BENCH') == '1':
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
        if self.bash_command is None:
            # Gemini flash not providing the tag and returns as code wrap in backticks
            self.bash_command = re.search(r'^```bash(.*)```$', action_str, re.DOTALL)
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
