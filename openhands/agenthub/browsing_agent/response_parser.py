import ast
import re

from openhands.controller.action_parser import ActionParser, ResponseParser
from openhands.core.logger import openhands_logger as logger
from openhands.events.action import (
    Action,
    BrowseInteractiveAction,
)


class BrowsingResponseParser(ResponseParser):
    def __init__(self) -> None:
        # Need to pay attention to the item order in self.action_parsers
        super().__init__()
        self.action_parsers = [BrowsingActionParserBrowseInteractive()]
        self.default_parser = BrowsingActionParserMessage()

    def parse(
        self, response: str | dict[str, list[dict[str, dict[str, str | None]]]]
    ) -> Action:
        if isinstance(response, str):
            action_str = response
        else:
            action_str = self.parse_response(response)
        return self.parse_action(action_str)

    def parse_response(
        self, response: dict[str, list[dict[str, dict[str, str | None]]]]
    ) -> str:
        action_str = response['choices'][0]['message']['content']
        if action_str is None:
            return ''
        action_str = action_str.replace(r'\_', '_')  # Mistral Large gives \_ instead of _
        # For Gemini:
        # ```tool_code
        # scroll(0, 200)
        # ```
        if '<execute_browse>' not in action_str:
            action_str = re.sub(
                r'```tool_code\n(.*)\n```',
                r'<execute_browse>\n\1\n</execute_browse>',
                action_str,
                re.DOTALL,
            )
        action_str = action_str.strip()
        start_tag = '<execute_browse>'
        end_tag = '</execute_browse>'
        if start_tag in action_str and end_tag not in action_str:
            action_str += end_tag
        logger.debug(action_str)
        return action_str

    def parse_action(self, action_str: str) -> Action:
        for action_parser in self.action_parsers:
            if action_parser.check_condition(action_str):
                return action_parser.parse(action_str)
        return self.default_parser.parse(action_str)


class BrowsingActionParserMessage(ActionParser):
    """Parser action:
    - BrowseInteractiveAction(browser_actions) - unexpected response format, message back to user
    """

    def __init__(self) -> None:
        pass

    def check_condition(self, action_str: str) -> bool:
        return True

    def parse(self, action_str: str) -> Action:
        msg = f'send_msg_to_user("""{action_str}""")'
        return BrowseInteractiveAction(
            browser_actions=msg,
            thought=action_str,
            browsergym_send_msg_to_user=action_str,
        )


class BrowsingActionParserBrowseInteractive(ActionParser):
    """Parser action:
    - BrowseInteractiveAction(browser_actions) - handle send message to user function call in BrowserGym
    """

    def __init__(self) -> None:
        pass

    def check_condition(self, action_str: str) -> bool:
        self.action_str = re.search(
            r'<execute_browse>(.*?)</execute_browse>', action_str, re.DOTALL
        )
        return self.action_str is not None

    def parse(self, action_str: str) -> Action:
        assert (
            self.action_str is not None
        ), 'self.action_str should not be None when parse is called'
        browser_actions = self.action_str.group(1).strip()
        thought = action_str.replace(self.action_str.group(0), '').strip()
        msg_content = ''
        for sub_action in browser_actions.split('\n'):
            if 'send_msg_to_user(' in sub_action:
                try:
                    tree = ast.parse(sub_action)
                    args = tree.body[0].value.args  # type: ignore
                    msg_content = args[0].value
                except SyntaxError:
                    logger.error(f'Error parsing action: {sub_action}')
                    # the syntax was not correct, but we can still try to get the message
                    # e.g. send_msg_to_user("Hello, world!") or send_msg_to_user('Hello, world!'
                    match = re.search(r'send_msg_to_user\((["\'])(.*?)\1\)', sub_action)
                    if match:
                        msg_content = match.group(2)
                    else:
                        msg_content = ''

        return BrowseInteractiveAction(
            browser_actions=browser_actions,
            thought=thought,
            browsergym_send_msg_to_user=msg_content,
        )
