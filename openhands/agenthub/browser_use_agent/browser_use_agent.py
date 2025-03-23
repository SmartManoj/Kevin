import asyncio
import nest_asyncio

from openhands.core.logger import openhands_logger as logger

nest_asyncio.apply()
import os
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import Agent as BrowserUseAgent_
from browser_use import BrowserConfig, Browser
from browser_use.browser.context import BrowserContext, BrowserContextConfig

from openhands.controller.state.state import State
from openhands.controller.agent import Agent
from openhands.core.config.agent_config import AgentConfig
from openhands.events.action.action import Action
from openhands.events.action.agent import AgentFinishAction
from openhands.llm.llm import LLM

from warnings import filterwarnings
from langchain_core._api import LangChainBetaWarning
filterwarnings("ignore", category=LangChainBetaWarning)

def get_llm(model, api_key = None, base_url = None):
    model_provider, model_name = model.split("/", 1)
    if model_provider.lower() == "gemini":
        return ChatGoogleGenerativeAI(model=model_name, api_key=api_key)
    else:
        return ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url)

class BrowserUseAgent(Agent):
    VERSION = '1.0'
    """
    An agent that interacts with the browser.
    """
    def __init__(
        self,
        llm: LLM,
        config: AgentConfig,
    ) -> None:
        """Initializes a new instance of the BrowsingAgent class.

        Parameters:
        - llm (LLM): The llm to be used by this agent
        """
        super().__init__(llm, config)
        self.langchain_llm = get_llm(llm.config.model, llm.config.api_key, llm.config.base_url)
        config = BrowserConfig(
            headless=os.getenv('BROWSER_HEADLESS', 'true').lower() in ['true','1'],
            disable_security=True
        )
        self.browser = Browser(config=config)
        self.browser_context = BrowserContext(browser=self.browser, config=BrowserContextConfig())
        self.loop = asyncio.new_event_loop()
        

    def step(self, state: State) -> Action:
        goal, _ = state.get_current_user_intent()

        if goal is None:
            goal = state.inputs['task']
        
        agent = BrowserUseAgent_(
            browser=self.browser,
            browser_context=self.browser_context,
            task=goal,
            llm=self.langchain_llm,
        )
        logger.info(f"Running agent with goal: {goal}")
        history = self.loop.run_until_complete(agent.run())
        last_action = history.last_action()
        result = last_action['done']['text']
        if not last_action['done']['success']:
            result = 'The task is failed.\n' + result
        print(result)
        return AgentFinishAction(thought=result, outputs={'content': result})

