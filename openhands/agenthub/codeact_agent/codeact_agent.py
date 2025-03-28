import os
import re
from collections import deque

from litellm import ModelResponse

import openhands
import openhands.agenthub.codeact_agent.function_calling as codeact_function_calling
from openhands.agenthub.codeact_agent.action_parser import CodeActResponseParser
from openhands.controller.agent import Agent
from openhands.controller.state.state import State
from openhands.core import config2
from openhands.core.config import AgentConfig, load_app_config
from openhands.core.logger import openhands_logger as logger
from openhands.core.message import ImageContent, Message, TextContent
from openhands.core.schema import ActionType
from openhands.events.action import (
    Action,
    AgentDelegateAction,
    AgentFinishAction,
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    IPythonRunCellAction,
    MessageAction,
)
from openhands.events.event import AudioEvent, EventSource, LogEvent
from openhands.events.observation import (
    AgentCondensationObservation,
    AgentDelegateObservation,
    BrowserOutputObservation,
    CmdOutputObservation,
    FileEditObservation,
    FileReadObservation,
    IPythonRunCellObservation,
    UserRejectObservation,
)
from openhands.events.observation.agent import RecallObservation
from openhands.events.observation.error import ErrorObservation
from openhands.events.observation.observation import Observation
from openhands.events.serialization.event import truncate_content
from openhands.events.event import Event
from openhands.llm.llm import LLM
from openhands.memory.condenser import Condenser
from openhands.memory.condenser.condenser import Condensation, View
from openhands.memory.conversation_memory import ConversationMemory
from openhands.runtime.plugins import (
    AgentSkillsRequirement,
    JupyterRequirement,
    PluginRequirement,
)
from openhands.runtime.plugins.vscode import VSCodeRequirement
from openhands.utils.prompt import PromptManager

config = load_app_config()


class CodeActAgent(Agent):
    VERSION = '2.2'
    """
    The Code Act Agent is a minimalist agent.
    The agent works by passing the model a list of action-observation pairs and prompting the model to take the next step.

    ### Overview

    This agent implements the CodeAct idea ([paper](https://arxiv.org/abs/2402.01030), [tweet](https://twitter.com/xingyaow_/status/1754556835703751087)) that consolidates LLM agents' **act**ions into a unified **code** action space for both *simplicity* and *performance* (see paper for more details).

    The conceptual idea is illustrated below. At each turn, the agent can:

    1. **Converse**: Communicate with humans in natural language to ask for clarification, confirmation, etc.
    2. **CodeAct**: Choose to perform the task by executing code
    - Execute any valid Linux `bash` command
    - Execute any valid `Python` code with [an interactive Python interpreter](https://ipython.org/). This is simulated through `bash` command, see plugin system below for more details.

    ![image](https://github.com/All-Hands-AI/OpenHands/assets/38853559/92b622e3-72ad-4a61-8f41-8c040b6d5fb3)

    """

    sandbox_plugins: list[PluginRequirement] = [
        # NOTE: AgentSkillsRequirement need to go before JupyterRequirement, since
        # AgentSkillsRequirement provides a lot of Python functions,
        # and it needs to be initialized before Jupyter for Jupyter to use those functions.
        AgentSkillsRequirement(),
        JupyterRequirement(),
        VSCodeRequirement(),
    ]

    def __init__(
        self,
        llm: LLM,
        config: AgentConfig,
    ) -> None:
        """Initializes a new instance of the CodeActAgent class.

        Parameters:
        - llm (LLM): The llm to be used by this agent
        """
        super().__init__(llm, config)
        self.pending_actions: deque[Action] = deque()
        self.reset()

        self.condenser = Condenser.from_config(self.config.condenser)
        logger.debug(f'Using condenser: {type(self.condenser)}')

        if not self.config.function_calling:
            self.action_parser = CodeActResponseParser()
            self.prompt_manager = PromptManager(
                microagent_dir=os.path.join(os.path.dirname(os.path.dirname(openhands.__file__)), 'microagents')
                if self.config.use_microagents
                else None,
                prompt_dir=os.path.join(
                    os.path.dirname(__file__), 'prompts', 'default'
                ),
                agent_skills_docs=AgentSkillsRequirement.documentation,
                disabled_microagents=self.config.disabled_microagents,
                use_bash=self.config.codeact_enable_bash,
                use_browser=self.config.codeact_enable_browsing,
            )
            return
        # Function calling mode
        self.tools = codeact_function_calling.get_tools(
            codeact_enable_browsing=self.config.codeact_enable_browsing,
            codeact_enable_jupyter=self.config.codeact_enable_jupyter,
            codeact_enable_llm_editor=self.config.codeact_enable_llm_editor,
            llm=self.llm,
        )
        logger.debug(
            f"TOOLS loaded for CodeActAgent: {', '.join([tool.get('function').get('name') for tool in self.tools])}"
        )
        self.prompt_manager = PromptManager(
            prompt_dir=os.path.join(os.path.dirname(__file__), 'prompts'),
        )

    def get_action_message(
        self,
        action: Action,
        pending_tool_call_action_messages: dict[str, Message],
    ) -> list[Message]:
        """Converts an action into a message format that can be sent to the LLM.

        This method handles different types of actions and formats them appropriately:
        1. For tool-based actions (AgentDelegate, CmdRun, IPythonRunCell, FileEdit) and agent-sourced AgentFinish:
            - In function calling mode: Stores the LLM's response in pending_tool_call_action_messages
            - In non-function calling mode: Creates a message with the action string
        2. For MessageActions: Creates a message with the text content and optional image content

        Args:
            action (Action): The action to convert. Can be one of:
                - CmdRunAction: For executing bash commands
                - IPythonRunCellAction: For running IPython code
                - FileEditAction: For editing files
                - FileReadAction: For reading files using openhands-aci commands
                - BrowseInteractiveAction: For browsing the web
                - AgentFinishAction: For ending the interaction
                - MessageAction: For sending messages
            pending_tool_call_action_messages (dict[str, Message]): Dictionary mapping response IDs
                to their corresponding messages. Used in function calling mode to track tool calls
                that are waiting for their results.

        Returns:
            list[Message]: A list containing the formatted message(s) for the action.
                May be empty if the action is handled as a tool call in function calling mode.

        Note:
            In function calling mode, tool-based actions are stored in pending_tool_call_action_messages
            rather than being returned immediately. They will be processed later when all corresponding
            tool call results are available.
        """
        # create a regular message from an event
        if isinstance(
            action,
            (
                AgentDelegateAction,
                IPythonRunCellAction,
                FileEditAction,
                FileReadAction,
                BrowseInteractiveAction,
                BrowseURLAction,
            ),
        ) or (isinstance(action, CmdRunAction) and action.source == 'agent'):
            if not self.config.function_calling:
                assert not isinstance(action, BrowseInteractiveAction), (
                    'BrowseInteractiveAction is not supported in non-function calling mode. Action: '
                    + str(action)
                )
                content = [TextContent(text=self.action_parser.action_to_str(action))]
                return [
                    Message(
                        role='user' if action.source == 'user' else 'assistant',
                        content=content,
                    )
                ]
            tool_metadata = action.tool_call_metadata
            llm_response: ModelResponse = tool_metadata._model_response  # type: ignore
            assistant_msg = llm_response.choices[0].message

            # Add the LLM message (assistant) that initiated the tool calls
            # (overwrites any previous message with the same response_id)
            logger.debug(
                f'Tool calls type: {type(assistant_msg.tool_calls)}, value: {assistant_msg.tool_calls}'
            )
            pending_tool_call_action_messages[llm_response.id] = Message(
                role=assistant_msg.role,
                # tool call content SHOULD BE a string
                content=[TextContent(text=assistant_msg.content or '')]
                if assistant_msg.content is not None
                else [],
                tool_calls=assistant_msg.tool_calls,
            )
            return []
        elif isinstance(action, AgentFinishAction):
            role = 'user' if action.source == 'user' else 'assistant'
            if not self.config.function_calling:
                content = [TextContent(text=self.action_parser.action_to_str(action))]
                return [
                    Message(
                        role='user' if action.source == 'user' else 'assistant',
                        content=content,
                    )
                ]
            # when agent finishes, it has tool_metadata
            # which has already been executed, and it doesn't have a response
            # when the user finishes (/exit), we don't have tool_metadata
            tool_metadata = action.tool_call_metadata
            if tool_metadata is not None:
                # take the response message from the tool call
                assistant_msg = tool_metadata._model_response.choices[0].message  # type: ignore
                content = assistant_msg.content or ''  # type: ignore

                # save content if any, to thought
                if action.thought:
                    if action.thought != content:
                        action.thought += '\n' + content  # type: ignore
                else:
                    action.thought = content  # type: ignore

                # remove the tool call metadata
                action.tool_call_metadata = None
            return [
                Message(
                    role=role,
                    content=[TextContent(text=action.thought)],
                )
            ]
        elif isinstance(action, MessageAction):
            role = 'user' if action.source == 'user' else 'assistant'
            content = [TextContent(text=action.content or '')]
            if self.llm.vision_is_active() and action.image_urls:
                content.append(ImageContent(image_urls=action.image_urls))
            return [
                Message(
                    role=role,
                    content=content,
                    event_id=action.id,
                )
            ]
        elif isinstance(action, CmdRunAction) and action.source == 'user':
            content = [
                TextContent(text=f'User executed the command:\n{action.command}')
            ]
            return [
                Message(
                    role='user',
                    content=content,
                )
            ]
        return []

    def get_observation_message(
        self,
        obs: Observation,
        tool_call_id_to_message: dict[str, Message],
    ) -> list[Message]:
        """Converts an observation into a message format that can be sent to the LLM.

        This method handles different types of observations and formats them appropriately:
        - CmdOutputObservation: Formats command execution results with exit codes
        - IPythonRunCellObservation: Formats IPython cell execution results, replacing base64 images
        - FileEditObservation: Formats file editing results
        - FileReadObservation: Formats file reading results from openhands-aci
        - AgentDelegateObservation: Formats results from delegated agent tasks
        - ErrorObservation: Formats error messages from failed actions
        - UserRejectObservation: Formats user rejection messages

        In function calling mode, observations with tool_call_metadata are stored in
        tool_call_id_to_message for later processing instead of being returned immediately.

        Args:
            obs (Observation): The observation to convert
            tool_call_id_to_message (dict[str, Message]): Dictionary mapping tool call IDs
                to their corresponding messages (used in function calling mode)

        Returns:
            list[Message]: A list containing the formatted message(s) for the observation.
                May be empty if the observation is handled as a tool response in function calling mode.

        Raises:
            ValueError: If the observation type is unknown
        """
        # max_message_chars = self.llm.config.max_message_chars
        max_message_chars = 10_000
        obs_prefix = 'OBSERVATION:\n'
        image_urls = []
        if isinstance(obs, CmdOutputObservation):
            ansi_color_escape = re.compile(r'\x1b\[[0-9;]*m')
            obs.content = ansi_color_escape.sub('', obs.content)
            if obs.tool_call_metadata is None:
                text = truncate_content(
                    f'\nObserved result of command executed by user:\n{obs.to_agent_observation()}',
                    max_message_chars,
                )
            else:
                text = truncate_content(obs.to_agent_observation(), max_message_chars)
        elif isinstance(obs, IPythonRunCellObservation):
            text = obs.content
            # replace base64 images with a placeholder
            splitted = text.split('\n')
            for i, line in enumerate(splitted):
                if '![image](data:image/png;base64,' in line:
                    splitted[i] = ''
                    image_urls.append(line[8:-1])
            text = '\n'.join(splitted)
            text = truncate_content(text, max_message_chars)
        elif isinstance(obs, FileEditObservation):
            text = truncate_content(str(obs), max_message_chars)
        elif isinstance(obs, FileReadObservation):
            text = obs.content
        elif isinstance(obs, BrowserOutputObservation):
            text = obs.get_agent_obs_text()
            if (
                obs.trigger_by_action == ActionType.BROWSE_INTERACTIVE
                and obs.set_of_marks is not None
                and len(obs.set_of_marks) > 0
                and self.config.enable_som_visual_browsing
                and self.llm.vision_is_active()
            ):
                text += 'Image: Current webpage screenshot (Note that only visible portion of webpage is present in the screenshot. You may need to scroll to view the remaining portion of the web-page.)\n'
        elif isinstance(obs, AgentDelegateObservation):
            text = truncate_content(
                obs.outputs['content'] if 'content' in obs.outputs else '',
                max_message_chars,
            )
        elif isinstance(obs, BrowserOutputObservation):
            text = obs_prefix + truncate_content(obs.content, max_message_chars)
            return Message(role='user', content=[TextContent(text=text)])
        elif isinstance(obs, ErrorObservation):
            text = truncate_content(obs.content, max_message_chars)
            text += '\n[Error occurred in processing last action]'
        elif isinstance(obs, UserRejectObservation):
            text = obs_prefix + truncate_content(obs.content, max_message_chars)
            text += '\n[Last action has been rejected by the user]'
        elif isinstance(obs, AgentCondensationObservation):
            text = truncate_content(obs.content, max_message_chars)
        elif isinstance(obs, RecallObservation):
            text = obs_prefix + truncate_content(obs.content, max_message_chars)
        else:
            # If an observation message is not returned, it will cause an error
            # when the LLM tries to return the next message
            raise ValueError(f'Unknown observation type: {type(obs)}')

        if self.config.function_calling:
            # Update the message as tool response properly
            if (tool_call_metadata := obs.tool_call_metadata) is not None:
                tool_call_id_to_message[tool_call_metadata.tool_call_id] = Message(
                    role='tool',
                    content=[TextContent(text=text)],
                    tool_call_id=tool_call_metadata.tool_call_id,
                    name=tool_call_metadata.function_name,
                )
                # No need to return the observation message
                # because it will be added by get_action_message when all the corresponding
                # tool calls in the SAME request are processed
                return []

        content = [TextContent(text=text)]
        if image_urls:
            content.append(ImageContent(image_urls=image_urls))
        return [
            Message(
                role='user',
                content=content,
                event_id=obs.id,
            )
        ]

    def reset(self) -> None:
        """Resets the CodeAct Agent."""
        super().reset()
        self.pending_actions.clear()

    def step(self, state: State) -> Action:
        """Performs one step using the CodeAct Agent.

        This includes gathering info on previous steps and prompting the model to make a command to execute.

        Parameters:
        - state (State): used to get updated info

        Returns:
        - CmdRunAction(command) - bash command to run
        - IPythonRunCellAction(code) - IPython code to run
        - AgentDelegateAction(agent, inputs) - delegate action for (sub)task
        - MessageAction(content) - Message action to run (e.g. ask for clarification)
        - AgentFinishAction() - end the interaction
        """
        # Continue with pending actions if any
        if self.pending_actions:
            return self.pending_actions.popleft()

        # if we're done, go back
        latest_user_message = state.get_last_user_message()
        if latest_user_message and latest_user_message.content.strip() == '/exit':
            return AgentFinishAction()

        # Condense the events from the state. If we get a view we'll pass those
        # to the conversation manager for processing, but if we get a condensation
        # event we'll just return that instead of an action. The controller will
        # immediately ask the agent to step again with the new view.
        condensed_history: list[Event] = []
        match self.condenser.condensed_history(state):
            case View(events=events):
                condensed_history = events

            case Condensation(action=condensation_action):
                return condensation_action

        logger.debug(
            f'Processing {len(condensed_history)} events from a total of {len(state.history)} events'
        )

        messages = self._get_messages(condensed_history)
        try:
            last_message_content = messages[-1].content[0].text.strip().splitlines()
            if len(last_message_content) >= 3:
                last_message_content = last_message_content[-3]
                if last_message_content.endswith('<end></end>'):
                    return AgentFinishAction(thought=os.getenv('finish_thought', ''))
            # if no current directory is in output, check the last line
            last_message_content = last_message_content[-1]
            if last_message_content.endswith('<end></end>'):
                return AgentFinishAction(thought=os.getenv('finish_thought', ''))
        except Exception as e:
            # logger.debug(f'Error in step: {e}')
            pass
        params: dict = {
            'messages': messages,
            'condense': True,
            'origin': 'Agent',
        }
        if self.config.function_calling:
            params['tools'] = self.tools
        else:
            params['stop'] = [
                '</execute_ipython>',
                '</execute_bash>',
                '</execute_browse>',
                '</file_edit>',
            ]
        if self.config.mind_voice:
            new_messages = messages.copy()
            # change the system message
            new_messages[0].content[
                0
            ].text = f"Tell your frustration/comments about the code in {self.config.mind_voice}'s native voice in a single line in colloquial {self.config.mind_voice_language} langauge."
            # ask the LLM to generate the mind voice
            new_messages.append(
                Message(
                    role='user',
                    content=[
                        TextContent(
                            text=f'Now generate the mind voice for the above observation in a single line in colloquial {self.config.mind_voice_language} langauge. Wrap it in <mind_voice></mind_voice> tags.'
                        )
                    ],
                )
            )
            params['messages'] = new_messages
            response = self.llm.completion(**params)
            # reset the params
            params['messages'] = messages
            try:
                _response = response.choices[0].message.content
                # extract the mind voice from the response
                mind_voice = (
                    _response.split('<mind_voice>')[1]
                    .split('</mind_voice>')[0]
                )
                logger.info(f'Mind voice: {mind_voice}')
                assert self.event_stream is not None
                self.event_stream.add_event(
                    AudioEvent(text_for_audio=mind_voice), EventSource.AGENT
                )
            except Exception as e:
                logger.error(f'Error in mind voice: {e} \n Response: {_response}')
        response = self.llm.completion(**params)
        if self.config.function_calling:
            actions = codeact_function_calling.response_to_actions(response)
            for action in actions:
                self.pending_actions.append(action)
            return self.pending_actions.popleft()
        else:
            return self.action_parser.parse(response)

    def _get_messages(self, events: list[Event]) -> list[Message]:
        system_role = 'user' if config2.model.startswith('o1-') else 'system'
        """Constructs the message history for the LLM conversation.

        This method builds a structured conversation history by processing events from the state
        and formatting them into messages that the LLM can understand. It handles both regular
        message flow and function-calling scenarios.

        The method performs the following steps:
        1. Initializes with system prompt and optional initial user message
        2. Processes events (Actions and Observations) into messages
        3. Handles tool calls and their responses in function-calling mode
        4. Manages message role alternation (user/assistant/tool)
        5. Applies caching for specific LLM providers (e.g., Anthropic)
        6. Adds environment reminders for non-function-calling mode

        Args:
            events: The list of events to convert to messages

        Returns:
            list[Message]: A list of formatted messages ready for LLM consumption, including:
                - System message with prompt
                - Initial user message (if configured)
                - Action messages (from both user and assistant)
                - Observation messages (including tool responses)
                - Environment reminders (in non-function-calling mode)

        Note:
            - In function-calling mode, tool calls and their responses are carefully tracked
              to maintain proper conversation flow
            - Messages from the same role are combined to prevent consecutive same-role messages
            - For Anthropic models, specific messages are cached according to their documentation
        """
        if not self.prompt_manager:
            raise Exception('Prompt Manager not instantiated.')
        if config.use_selenium:
            extra_message = """

You have access to a selenium browser. You can use it using the driver python variable.

Example:
<execute_ipython>
driver.current_url
</execute_ipython>

To get a screenshot of the current page, use the following function:
<execute_ipython>
# Renders only when it is in the last line of the response.
display.Image(dss())
</execute_ipython>

"""
        else:
            extra_message = ''
        messages: list[Message] = [
            Message(
                role=system_role,
                content=[
                    TextContent(
                        text=self.prompt_manager.get_system_message() + extra_message,
                        cache_prompt=self.llm.is_caching_prompt_active(),
                    )
                ],
                condensable=False,
            ),
        ]
        user_contents = []
        
        if (
            len(events) == 1
            and config.run_as_openhands
            and config.show_workspace_contents
        ):
            workspace_contents = ', '.join(os.listdir(config.workspace_base))
            if workspace_contents:
                user_contents.append(
                    TextContent(
                        text=f'WORKSPACE CONTENTS: {workspace_contents}\n\n----------\n'
                    )
                )

        custom_instructions = config.custom_instructions
        if custom_instructions:
            user_contents.append(
                TextContent(text=custom_instructions)
            )
        # if state.history.summary:
        #     summary_message = self.get_action_message(
        #         state.history.summary, pending_tool_call_action_messages={}
        #     )
        #     if summary_message:
        #         messages.extend(summary_message)

        # TODO: delegation.
        # if task := state.inputs.get('task'):
        #     user_contents.append(TextContent(text=task))
        
        if user_contents:
            messages.append(
                Message(
                    role='user',
                    content=user_contents,
                    condensable=False,
                    cache_prompt=self.llm.is_caching_prompt_active(),
                ),
            )
        pending_tool_call_action_messages: dict[str, Message] = {}
        tool_call_id_to_message: dict[str, Message] = {}

        # Condense the events from the state.
        is_first_message_handled = False
        for k, event in enumerate(events):
            # create a regular message from an event
            if isinstance(event, Action):
                # SLM_Tweak
                # if ipython action, check next observation and modify the code
                if isinstance(event, IPythonRunCellAction):
                    if k + 1 < len(events):
                        next_obs = events[k + 1]
                        if isinstance(next_obs, IPythonRunCellObservation):
                            event.code = next_obs.code
                messages_to_add = self.get_action_message(
                    action=event,
                    pending_tool_call_action_messages=pending_tool_call_action_messages,
                )
            elif isinstance(event, Observation):
                messages_to_add = self.get_observation_message(
                    obs=event,
                    tool_call_id_to_message=tool_call_id_to_message,
                )
            elif isinstance(event, (LogEvent, AudioEvent)):
                continue
            else:
                raise ValueError(f'Unknown event type: {type(event)}')

            # Check pending tool call action messages and see if they are complete
            _response_ids_to_remove = []
            for (
                response_id,
                pending_message,
            ) in pending_tool_call_action_messages.items():
                assert pending_message.tool_calls is not None, (
                    'Tool calls should NOT be None when function calling is enabled & the message is considered pending tool call. '
                    f'Pending message: {pending_message}'
                )
                if all(
                    tool_call.id in tool_call_id_to_message
                    for tool_call in pending_message.tool_calls
                ):
                    # If complete:
                    # -- 1. Add the message that **initiated** the tool calls
                    messages_to_add.append(pending_message)
                    # -- 2. Add the tool calls **results***
                    for tool_call in pending_message.tool_calls:
                        messages_to_add.append(tool_call_id_to_message[tool_call.id])
                        tool_call_id_to_message.pop(tool_call.id)
                    _response_ids_to_remove.append(response_id)
            # Cleanup the processed pending tool messages
            for response_id in _response_ids_to_remove:
                pending_tool_call_action_messages.pop(response_id)

            for msg in messages_to_add:
                if msg:
                    # already handled the first user message
                    if msg.role == 'user' and not is_first_message_handled:
                        is_first_message_handled = True
                        # compose the first user message with examples
                        self.prompt_manager.add_examples_to_initial_message(msg)

                    messages.append(msg)

        if self.llm.is_caching_prompt_active():
            # NOTE: this is only needed for anthropic
            # following logic here:
            # https://github.com/anthropics/anthropic-quickstarts/blob/8f734fd08c425c6ec91ddd613af04ff87d70c5a0/computer-use-demo/computer_use_demo/loop.py#L241-L262
            breakpoints_remaining = 3  # remaining 1 for system/tool
            for message in reversed(messages):
                if message.role in ('user', 'tool'):
                    if breakpoints_remaining > 0:
                        message.content[
                            -1
                        ].cache_prompt = True  # Last item inside the message content
                        breakpoints_remaining -= 1
                    else:
                        break

        return messages

    def _enhance_messages(self, messages: list[Message]) -> list[Message]:
        """Enhances the user message with additional context based on keywords matched.

        Args:
            messages (list[Message]): The list of messages to enhance

        Returns:
            list[Message]: The enhanced list of messages
        """
        assert self.prompt_manager, 'Prompt Manager not instantiated.'

        results: list[Message] = []
        is_first_message_handled = False
        prev_role = None

        for msg in messages:
            if msg.role == 'user' and not is_first_message_handled:
                is_first_message_handled = True
                # compose the first user message with examples
                self.prompt_manager.add_examples_to_initial_message(msg)

            elif msg.role == 'user':
                # Add double newline between consecutive user messages
                if prev_role == 'user' and len(msg.content) > 0:
                    # Find the first TextContent in the message to add newlines
                    for content_item in msg.content:
                        if isinstance(content_item, TextContent):
                            # If the previous message was also from a user, prepend two newlines to ensure separation
                            content_item.text = '\n\n' + content_item.text
                            break

            results.append(msg)
            prev_role = msg.role

        return results
