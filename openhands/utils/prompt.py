import os
from dataclasses import dataclass, field
from itertools import islice

from jinja2 import Template

from openhands.controller.state.state import State
from openhands.core.message import Message, TextContent
from openhands.events.observation.agent import MicroagentKnowledge
from openhands.microagent.microagent import BaseMicroAgent, load_microagents_from_dir


@dataclass
class RuntimeInfo:
    available_hosts: dict[str, int] = field(default_factory=dict)
    additional_agent_instructions: str = ''


@dataclass
class RepositoryInfo:
    """Information about a GitHub repository that has been cloned."""

    repo_name: str | None = None
    repo_directory: str | None = None


class PromptManager:
    """
    Manages prompt templates and includes information from the user's workspace micro-agents and global micro-agents.

    This class is dedicated to loading and rendering prompts (system prompt, user prompt).

    Attributes:
        prompt_dir: Directory containing prompt templates.
    """

    def __init__(
        self,
        prompt_dir: str,
        microagent_dir: str | None = None,
        agent_skills_docs: str = '',
        disabled_microagents: list[str] | None = None,
        use_bash: bool = True,
        use_browser: bool = False,
    ):
        self.prompt_dir: str = prompt_dir
        self.agent_skills_docs: str = agent_skills_docs
        self.repository_info: RepositoryInfo | None = None
        self.system_template: Template = self._load_template('system_prompt')
        self.user_template: Template = self._load_template('user_prompt')
        self.additional_info_template: Template = self._load_template('additional_info')
        self.microagent_info_template: Template = self._load_template('microagent_info')
        self.runtime_info = RuntimeInfo(
            available_hosts={}, additional_agent_instructions=''
        )

        

        self.use_bash = use_bash
        self.use_browser = use_browser

        if microagent_dir:
            # This loads micro-agents from the microagent_dir
            # which is typically the OpenHands/microagents (i.e., the PUBLIC microagents)

            # Only load KnowledgeMicroAgents
            repo_microagents, knowledge_microagents, _ = load_microagents_from_dir(
                microagent_dir
            )
            

    def _load_template(self, template_name: str) -> Template:
        if self.prompt_dir is None:
            raise ValueError('Prompt directory is not set')
        template_path = os.path.join(self.prompt_dir, f'{template_name}.j2')
        if not os.path.exists(template_path):
            raise FileNotFoundError(f'Prompt file {template_path} not found')
        with open(template_path, 'r') as file:
            return Template(file.read())

    def get_system_message(self) -> str:
        return self.system_template.render(
            agent_skills_docs=self.agent_skills_docs,
            use_bash=self.use_bash,
            use_browser=self.use_browser,
        ).strip()

    def get_example_user_message(self) -> str:
        """This is the initial user message provided to the agent
        before *actual* user instructions are provided.

        It is used to provide a demonstration of how the agent
        should behave in order to solve the user's task. And it may
        optionally contain some additional context about the user's task.
        These additional context will convert the current generic agent
        into a more specialized agent that is tailored to the user's task.
        """

        return self.user_template.render().strip()

    def add_examples_to_initial_message(self, message: Message) -> None:
        """Add example_message to the first user message."""
        example_message = self.get_example_user_message() or None

        # Insert it at the start of the TextContent list
        if example_message:
            message.content.insert(0, TextContent(text=example_message))

    def build_workspace_context(
        self,
        message: Message,
    ) -> None:
        """Adds information about the repository and runtime to the initial user message.

        Args:
            message: The initial user message to add information to.
        """
        repo_instructions = ''
        assert (
            len(self.repo_microagents) <= 1
        ), f'Expecting at most one repo microagent, but found {len(self.repo_microagents)}: {self.repo_microagents.keys()}'
        for microagent in self.repo_microagents.values():
            # We assume these are the repo instructions
            if repo_instructions:
                repo_instructions += '\n\n'
            repo_instructions += microagent.content

        server_keywords = ['fastapi', 'flask', 'django']
        is_runtime_info_needed = any(keyword in repo_instructions for keyword in server_keywords)


        additional_info = self.additional_info_template.render(
            repository_instructions=repo_instructions,
            repository_info=self.repository_info,
            runtime_info=self.runtime_info if is_runtime_info_needed else None,
        ).strip()

    def build_microagent_info(
        self,
        triggered_agents: list[MicroagentKnowledge],
    ) -> str:
        """Renders the microagent info template with the triggered agents.

        Args:
            triggered_agents: A list of MicroagentKnowledge objects containing information
                              about triggered microagents.
        """
        return self.microagent_info_template.render(
            triggered_agents=triggered_agents
        ).strip()

    def add_turns_left_reminder(self, messages: list[Message], state: State) -> None:
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
            reminder_text = f'\n\nENVIRONMENT REMINDER: You have {state.max_iterations - state.iteration +2} turns left to complete the task. When finished reply with <finish></finish>.'
            latest_user_message.content.append(TextContent(text=reminder_text))
