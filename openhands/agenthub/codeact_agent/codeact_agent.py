import os
import re
from itertools import islice

from openhands.agenthub.codeact_agent.action_parser import CodeActResponseParser
from openhands.controller.agent import Agent
from openhands.controller.state.state import State
from openhands.core import config2
from openhands.core.config import AgentConfig, load_app_config
from openhands.core.message import ImageContent, Message, TextContent
from openhands.events.action import (
    Action,
    AgentDelegateAction,
    AgentFinishAction,
    AgentSummarizeAction,
    CmdRunAction,
    IPythonRunCellAction,
    MessageAction,
)
from openhands.events.action.browse import BrowseURLAction
from openhands.events.event import LogEvent
from openhands.events.observation import (
    AgentDelegateObservation,
    CmdOutputObservation,
    IPythonRunCellObservation,
    UserRejectObservation,
)
from openhands.events.observation.browse import BrowserOutputObservation
from openhands.events.observation.error import ErrorObservation
from openhands.events.observation.observation import Observation
from openhands.events.serialization.event import truncate_content
from openhands.llm.llm import LLM
from openhands.runtime.plugins import (
    AgentSkillsRequirement,
    JupyterRequirement,
    PluginRequirement,
)
from openhands.utils.microagent import MicroAgent
from openhands.utils.prompt import PromptManager

config = load_app_config()


class CodeActAgent(Agent):
    VERSION = '1.9'
    """
    The Code Act Agent is a minimalist agent.
    The agent works by passing the model a list of action-observation pairs and prompting the model to take the next step.

    ### Overview

    This agent implements the CodeAct idea ([paper](https://arxiv.org/abs/2402.01030), [tweet](https://twitter.com/xingyaow_/status/1754556835703751087)) that consolidates LLM agents’ **act**ions into a unified **code** action space for both *simplicity* and *performance* (see paper for more details).

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
    ]

    action_parser = CodeActResponseParser()

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
        self.reset()

        self.micro_agent = (
            MicroAgent(
                os.path.join(
                    os.path.dirname(__file__), 'micro', f'{config.micro_agent_name}.md'
                )
            )
            if config.micro_agent_name
            else None
        )

        self.prompt_manager = PromptManager(
            prompt_dir=os.path.join(os.path.dirname(__file__)),
            agent_skills_docs=AgentSkillsRequirement.documentation,
            micro_agent=self.micro_agent,
        )

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
            return action.thought
        return ''

    @classmethod
    def get_action_message(self, action: Action) -> Message | None:
        if (
            isinstance(action, AgentDelegateAction)
            or isinstance(action, CmdRunAction)
            or isinstance(action, IPythonRunCellAction)
            or isinstance(action, MessageAction)
            or isinstance(action, BrowseURLAction)
            or isinstance(action, AgentSummarizeAction)
            or (isinstance(action, AgentFinishAction) and action.source == 'agent')
        ):
            content = [TextContent(text=self.action_to_str(action))]

            if (
                # self.llm.vision_is_active()
                isinstance(action, MessageAction) and action.images_urls
            ):
                content.append(ImageContent(image_urls=action.images_urls))

            return Message(
                role='user' if action.source == 'user' else 'assistant',
                content=content,
                event_id=action.id,
            )
        return None

    @classmethod
    def get_observation_message(self, obs: Observation) -> Message | None:
        # max_message_chars = self.llm.config.max_message_chars
        max_message_chars = 10_000
        obs_prefix = 'OBSERVATION:\n'
        if isinstance(obs, CmdOutputObservation):
            ansi_color_escape = re.compile(r'\x1b\[[0-9;]*m')
            obs.content = ansi_color_escape.sub('', obs.content)
            text = obs_prefix + truncate_content(obs.content, max_message_chars)
            if obs.exit_code != 0:
                text += f'\n[Command finished with exit code {obs.exit_code}. Why did you run this command?]'
            # text += (
            #     f'\n[Command finished with exit code {obs.exit_code}]'
            # )
        elif isinstance(obs, IPythonRunCellObservation):
            text = obs_prefix + obs.content
            # replace base64 images with a placeholder
            splitted = text.split('\n')
            for i, line in enumerate(splitted):
                if '![image](data:image/png;base64,' in line:
                    splitted[i] = (
                        '![image](data:image/png;base64, ...) already displayed to user'
                    )
            text = '\n'.join(splitted)
            text = truncate_content(text, max_message_chars)
        elif isinstance(obs, AgentDelegateObservation):
            text = obs_prefix + truncate_content(
                obs.outputs['content'] if 'content' in obs.outputs else '',
                max_message_chars,
            )
        elif isinstance(obs, BrowserOutputObservation):
            text = obs_prefix + truncate_content(obs.content, max_message_chars)
            return Message(role='user', content=[TextContent(text=text)])
        elif isinstance(obs, ErrorObservation):
            text = obs_prefix + truncate_content(obs.content, max_message_chars)
            text += '\n[Error occurred in processing last action]'
        elif isinstance(obs, UserRejectObservation):
            text = obs_prefix + truncate_content(obs.content, max_message_chars)
            text += '\n[Last action has been rejected by the user]'
        else:
            # If an observation message is not returned, it will cause an error
            # when the LLM tries to return the next message
            raise ValueError(f'Unknown observation type: {type(obs)}')
        return Message(
            role='user',
            content=[TextContent(text=text)],
            event_id=obs.id,
        )

    def reset(self) -> None:
        """Resets the CodeAct Agent."""
        super().reset()

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
        # if we're done, go back
        latest_user_message = state.history.get_last_user_message()
        if latest_user_message and latest_user_message.strip() == '/exit':
            return AgentFinishAction()

        response = None
        # prepare what we want to send to the LLM
        messages = self._get_messages(state)
        try:
            last_message_content = messages[-1].content[0].text.strip().splitlines()[-3]
            if last_message_content.endswith('<end></end>'):
                return AgentFinishAction(thought=os.getenv('finish_thought', ''))
        except Exception as e:
            print(e)
        params = {
            'messages': messages,
            'stop': [
                '</execute_ipython>',
                '</execute_bash>',
                '</execute_browse>',
            ],
            'condense': True,
            'origin': 'Agent',
        }

        response = self.llm.completion(**params)

        return self.action_parser.parse(response)

    def _get_messages(self, state: State) -> list[Message]:
        system_role = 'user' if config2.model.startswith('o1-') else 'system'
        messages: list[Message] = [
            Message(
                role=system_role,
                content=[
                    TextContent(
                        text=self.prompt_manager.system_message,
                        cache_prompt=self.llm.is_caching_prompt_active(),  # Cache system prompt
                    )
                ],
                condensable=False,
            ),
            Message(
                role='user',
                content=[
                    TextContent(
                        text=self.prompt_manager.initial_user_message,
                        cache_prompt=self.llm.is_caching_prompt_active(),  # if the user asks the same query,
                    )
                ],
                condensable=False,
            ),
        ]

        if len(state.history.get_events_as_list()) == 1 and config.run_as_openhands:
            workspace_contents = ', '.join(os.listdir(config.workspace_base))
            if workspace_contents:
                messages.append(
                    Message(
                        role='user',
                        content=[
                            TextContent(
                                text=f'WORKSPACE CONTENTS: {workspace_contents}'
                            )
                        ],
                    )
                )

        if state.history.summary:
            summary_message = self.get_action_message(state.history.summary)
            if summary_message:
                messages.append(summary_message)
        for event in state.history.get_events():
            if event.id > state.history.last_summarized_event_id:
                # create a regular message from an event
                if isinstance(event, Action):
                    message = self.get_action_message(event)
                elif isinstance(event, Observation):
                    message = self.get_observation_message(event)
                elif isinstance(event, LogEvent):
                    message = None
                else:
                    raise ValueError(f'Unknown event type: {type(event)}')
                # add regular message
                if message:
                    # handle error if the message is the SAME role as the previous message
                    # litellm.exceptions.BadRequestError: litellm.BadRequestError: OpenAIException - Error code: 400 - {'detail': 'Only supports u/a/u/a/u...'}
                    # there shouldn't be two consecutive messages from the same role
                    if messages and messages[-1].role == message.role:
                        messages[-1].content.extend(message.content)
                    else:
                        messages.append(message)

        # Add caching to the last 2 user messages
        if self.llm.is_caching_prompt_active():
            user_turns_processed = 0
            for message in reversed(messages):
                if message.role == 'user' and user_turns_processed < 2:
                    message.content[
                        -1
                    ].cache_prompt = True  # Last item inside the message content
                    user_turns_processed += 1

        # The latest user message is important:
        # we want to remind the agent of the environment constraints
        latest_user_message = next(
            islice(
                (
                    m
                    for m in reversed(messages)
                    if m.role == 'user'
                    and any(isinstance(c, TextContent) for c in m.content)
                ),
                1,
            ),
            None,
        )
        if latest_user_message:
            reminder_text = f'\n\nENVIRONMENT REMINDER: You have {state.max_iterations - state.iteration + 2} turns left to complete the task. When finished, please reply with <finish></finish>.'
            latest_user_message.content.append(TextContent(text=reminder_text))

        return messages
