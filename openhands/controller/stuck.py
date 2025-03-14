from openhands.agenthub.codeact_agent.codeact_agent import CodeActAgent
from openhands.controller.state.state import State
from openhands.core.logger import openhands_logger as logger
from openhands.core.message import Message, TextContent
from openhands.events.action.action import Action
from openhands.events.action.commands import IPythonRunCellAction
from openhands.events.action.empty import NullAction
from openhands.events.action.message import MessageAction
from openhands.events.event import Event, EventSource
from openhands.events.observation import (
    CmdOutputObservation,
    IPythonRunCellObservation,
)
from openhands.events.observation.agent import AgentCondensationObservation
from openhands.events.observation.empty import NullObservation
from openhands.events.observation.error import ErrorObservation
from openhands.events.observation.observation import Observation
from openhands.llm.llm import LLM


class StuckDetector:
    SYNTAX_ERROR_MESSAGES = [
        'SyntaxError: unterminated string literal (detected at line',
        'SyntaxError: invalid syntax. Perhaps you forgot a comma?',
        'SyntaxError: incomplete input',
    ]

    def __init__(self, state: State, agent: CodeActAgent, llm: LLM):
        self.state = state
        self.agent = agent
        self.llm = llm

    def generate_resolution(self, actions, observations):
        #
        struck_prompt = 'You analyze the history to find out why the agent is stuck and generate a resolution'
        # stuck input
        stuck_input = 'Aanalyze the history'
        for index, (action, observation) in enumerate(zip(actions, observations), 1):
            action = self.agent.get_action_message(
                action, pending_tool_call_action_messages={}
            )
            observation = self.agent.get_observation_message(
                observation, tool_call_id_to_message={}
            )
            stuck_input += f'\n{index = }. {action = }\n{observation = }'

        message_sequence = []
        message_sequence.append(
            Message(role='system', content=[TextContent(text=struck_prompt)])
        )
        message_sequence.append(
            Message(role='user', content=[TextContent(text=stuck_input)])
        )

        response = self.llm.completion(
            messages=message_sequence,
            temperature=0.0,
            condense=True,
        )
        return response.choices[0].message.content

    def get_last_event_pairs(
        self, history: list[Event], n: int
    ) -> tuple[list[Event], list[Event]]:
        if len(history) < n:
            return [], []

        last_actions: list[Event] = []
        last_observations: list[Event] = []

        for event in reversed(history):
            if isinstance(event, Action) and len(last_actions) < n:
                last_actions.append(event)
            elif isinstance(event, Observation) and len(last_observations) < n:
                last_observations.append(event)

            if len(last_actions) == n and len(last_observations) == n:
                break

        return last_actions, last_observations

    def is_stuck(self, headless_mode: bool = True):
        """Checks if the agent is stuck in a loop.

        Args:
            headless_mode: Matches AgentController's headless_mode.
                          If True: Consider all history (automated/testing)
                          If False: Consider only history after last user message (interactive)

        Returns:
            bool: True if the agent is stuck in a loop, False otherwise.
        """
        if not headless_mode:
            # In interactive mode, only look at history after the last user message
            last_user_msg_idx = -1
            for i, event in enumerate(reversed(self.state.history)):
                if (
                    isinstance(event, MessageAction)
                    and event.source == EventSource.USER
                ):
                    last_user_msg_idx = len(self.state.history) - i - 1
                    break

            history_to_check = self.state.history[last_user_msg_idx + 1 :]
        else:
            # In headless mode, look at all history
            history_to_check = self.state.history

        # Filter out user messages and null events
        filtered_history = [
            event
            for event in history_to_check
            if not (
                # Filter works elegantly in both modes:
                # - In headless: actively filters out user messages from full history
                # - In non-headless: no-op since we already sliced after last user message
                (isinstance(event, MessageAction) and event.source == EventSource.USER)
                # there might be some NullAction or NullObservation in the history at least for now
                or isinstance(event, (NullAction, NullObservation))
            )
        ]
        step_count = 2
        last_actions, last_observations = self.get_last_event_pairs(
            filtered_history, step_count
        )

        if not len(last_actions) == len(last_observations) == step_count:
            return False, None

        # scenario 1: same action, same observation
        if self._is_stuck_repeating_action_observation(last_actions, last_observations):
            return True, self.generate_resolution(last_actions, last_observations)

        # scenario 2: same action, errors
        if self._is_stuck_repeating_action_error(last_actions, last_observations):
            return True, self.generate_resolution(last_actions, last_observations)

        # scenario 3: monologue
        if self._is_stuck_monologue(filtered_history):
            return True, 'You repeated the same message three times'

        # scenario 4: action, observation pattern on the last four steps
        step_count = 4
        last_actions, last_observations = self.get_last_event_pairs(
            filtered_history, step_count
        )
        if not len(last_actions) == len(last_observations) == step_count:
            return False, None
        if self._is_stuck_action_observation_pattern(last_actions, last_observations):
            # (action_1, obs_1), (action_2, obs_2), (action_1, obs_1), (action_2, obs_2)
            return True, self.generate_resolution(last_actions, last_observations)

        # scenario 5: context window error loop
        if len(filtered_history) >= 10:
            if self._is_stuck_context_window_error(filtered_history):
                return True

        return False, None

    def _is_stuck_repeating_action_observation(self, last_actions, last_observations):
        # scenario 1: same action, same observation

        actions_equal = all(
            self._eq_no_pid(last_actions[0], action) for action in last_actions
        )
        observations_equal = all(
            self._eq_no_pid(last_observations[0], observation)
            for observation in last_observations
        )

        if actions_equal and observations_equal:
            logger.warning('Action, Observation loop detected')
            return True

        return False

    def _is_stuck_repeating_action_error(self, last_actions, last_observations):
        # scenario 2: same action, errors

        # are the last three actions the "same"?
        if all(self._eq_no_pid(last_actions[0], action) for action in last_actions[:3]):
            # and the last three observations are all errors?
            if all(isinstance(obs, ErrorObservation) for obs in last_observations[:3]):
                logger.warning('Action, ErrorObservation loop detected')
                return True
            # or, are the last three observations all IPythonRunCellObservation with SyntaxError?
            elif all(
                isinstance(obs, IPythonRunCellObservation)
                for obs in last_observations[:3]
            ):
                warning = 'Action, IPythonRunCellObservation loop detected'
                for error_message in self.SYNTAX_ERROR_MESSAGES:
                    if error_message.startswith(
                        'SyntaxError: unterminated string literal (detected at line'
                    ):
                        if self._check_for_consistent_line_error(
                            last_observations[:3], error_message
                        ):
                            logger.warning(warning)
                            return True
                    elif error_message in (
                        'SyntaxError: invalid syntax. Perhaps you forgot a comma?',
                        'SyntaxError: incomplete input',
                    ) and self._check_for_consistent_invalid_syntax(
                        last_observations[:3], error_message
                    ):
                        logger.warning(warning)
                        return True
        return False

    def _check_for_consistent_invalid_syntax(self, observations, error_message):
        first_lines = []
        valid_observations = []

        for obs in observations:
            content = obs.content
            lines = content.strip().split('\n')

            if len(lines) < 6:  # 6 because a real syntax error has at least 6 lines
                return False

            line1 = lines[0].strip()
            if not line1.startswith('Cell In[1], line'):
                return False

            first_lines.append(line1)  # Store the first line of each observation

            # Check last three lines
            if (
                lines[-1].startswith('[Jupyter Python interpreter:')
                and lines[-2].startswith('[Jupyter current working directory:')
                and error_message in lines[-3]
            ):
                valid_observations.append(obs)

        # Check if:
        # 1. All first lines are identical
        # 2. We have exactly 3 valid observations
        # 3. The error message line is identical in all valid observations
        return (
            len(set(first_lines)) == 1
            and len(valid_observations) == 3
            and len(
                set(
                    obs.content.strip().split('\n')[:-2][-1]
                    for obs in valid_observations
                )
            )
            == 1
        )

    def _check_for_consistent_line_error(self, observations, error_message):
        error_lines = []

        for obs in observations:
            content = obs.content
            lines = content.strip().split('\n')

            if len(lines) < 3:
                return False

            last_lines = lines[-3:]

            # Check if the last two lines are our own
            if not (
                last_lines[-2].startswith('[Jupyter current working directory:')
                and last_lines[-1].startswith('[Jupyter Python interpreter:')
            ):
                return False

            # Check for the error message in the 3rd-to-last line
            if error_message in last_lines[-3]:
                error_lines.append(last_lines[-3])

        # Check if we found the error message in all 3 observations
        # and the 3rd-to-last line is identical across all occurrences
        return len(error_lines) == 3 and len(set(error_lines)) == 1

    def _is_stuck_monologue(self, filtered_history):
        # scenario 3: monologue
        # check for repeated MessageActions with source=AGENT
        # see if the agent is engaged in a good old monologue, telling itself the same thing over and over
        agent_message_actions = [
            (i, event)
            for i, event in enumerate(filtered_history)
            if isinstance(event, MessageAction) and event.source == EventSource.AGENT
        ]

        # last three message actions will do for this check
        if len(agent_message_actions) >= 3:
            last_agent_message_actions = agent_message_actions[-3:]

            if all(
                (last_agent_message_actions[0][1] == action[1])
                for action in last_agent_message_actions
            ):
                # check if there are any observations between the repeated MessageActions
                # then it's not yet a loop, maybe it can recover
                start_index = last_agent_message_actions[0][0]
                end_index = last_agent_message_actions[-1][0]

                has_observation_between = False
                for event in filtered_history[start_index + 1 : end_index]:
                    if isinstance(event, Observation):
                        has_observation_between = True
                        break

                if not has_observation_between:
                    logger.warning('Repeated MessageAction with source=AGENT detected')
                    return True
        return False

    def _is_stuck_action_observation_pattern(
        self, last_six_actions, last_six_observations
    ):
        # scenario 4: action, observation pattern on the last six steps
        # check if the agent repeats the same (Action, Observation)
        # every other step in the last six steps

        # this pattern is every other step, like:
        # (action_1, obs_1), (action_2, obs_2), (action_1, obs_1), (action_2, obs_2),...
        if len(last_six_actions) == 6 and len(last_six_observations) == 6:
            actions_equal = (
                # action_0 == action_2 == action_4
                self._eq_no_pid(last_six_actions[0], last_six_actions[2])
                and self._eq_no_pid(last_six_actions[0], last_six_actions[4])
                # action_1 == action_3 == action_5
                and self._eq_no_pid(last_six_actions[1], last_six_actions[3])
                and self._eq_no_pid(last_six_actions[1], last_six_actions[5])
            )
            observations_equal = (
                # obs_0 == obs_2 == obs_4
                self._eq_no_pid(last_six_observations[0], last_six_observations[2])
                and self._eq_no_pid(last_six_observations[0], last_six_observations[4])
                # obs_1 == obs_3 == obs_5
                and self._eq_no_pid(last_six_observations[1], last_six_observations[3])
                and self._eq_no_pid(last_six_observations[1], last_six_observations[5])
            )

            if actions_equal and observations_equal:
                logger.warning('Action, Observation pattern detected')
                return True
        return False

    def _is_stuck_context_window_error(self, filtered_history):
        """Detects if we're stuck in a loop of context window errors.

        This happens when we repeatedly get context window errors and try to trim,
        but the trimming doesn't work, causing us to get more context window errors.
        The pattern is repeated AgentCondensationObservation events without any other
        events between them.

        Args:
            filtered_history: List of filtered events to check

        Returns:
            bool: True if we detect a context window error loop
        """
        # Look for AgentCondensationObservation events
        condensation_events = [
            (i, event)
            for i, event in enumerate(filtered_history)
            if isinstance(event, AgentCondensationObservation)
        ]

        # Need at least 10 condensation events to detect a loop
        if len(condensation_events) < 10:
            return False

        # Get the last 10 condensation events
        last_condensation_events = condensation_events[-10:]

        # Check if there are any non-condensation events between them
        for i in range(len(last_condensation_events) - 1):
            start_idx = last_condensation_events[i][0]
            end_idx = last_condensation_events[i + 1][0]

            # Look for any non-condensation events between these two
            has_other_events = False
            for event in filtered_history[start_idx + 1 : end_idx]:
                if not isinstance(event, AgentCondensationObservation):
                    has_other_events = True
                    break

            if not has_other_events:
                logger.warning(
                    'Context window error loop detected - repeated condensation events'
                )
                return True

        return False

    def _eq_no_pid(self, obj1, obj2):
        if isinstance(obj1, IPythonRunCellAction) and isinstance(
            obj2, IPythonRunCellAction
        ):
            # for loop detection on edit actions, ignore the thought, compare some code
            # the code should have at least 3 lines, to avoid simple one-liners
            if (
                'edit_file_by_replace(' in obj1.code
                and 'edit_file_by_replace(' in obj2.code
            ):
                return (
                    len(obj1.code.split('\n')) > 2
                    and obj1.code.split('\n')[:3] == obj2.code.split('\n')[:3]
                )
            else:
                # default comparison
                return obj1 == obj2
        elif isinstance(obj1, CmdOutputObservation) and isinstance(
            obj2, CmdOutputObservation
        ):
            # for loop detection, ignore command_id, which is the pid
            return obj1.command == obj2.command and obj1.exit_code == obj2.exit_code
        else:
            # this is the default comparison
            return obj1 == obj2
