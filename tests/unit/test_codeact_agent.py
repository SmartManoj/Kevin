import pytest

from agenthub.codeact_agent.codeact_agent import CodeActAgent
from opendevin.controller.state.state import State
from opendevin.events.action import CmdRunAction, IPythonRunCellAction, BrowseInteractiveAction

@pytest.fixture
def agent():
    return CodeActAgent(None)

@pytest.fixture
def state():
    return State()

def test_execute_bash_first_command(agent, state):
    action_str = "<execute_bash>echo 'Hello World'</execute_bash><execute_ipython>print('Hello World')</execute_ipython>"
    action = agent.step(state, action_str)
    assert isinstance(action, CmdRunAction)
    assert action.command == "echo 'Hello World'"

def test_ignore_subsequent_commands_if_bash_first(agent, state):
    action_str = "<execute_bash>echo 'Hello World'</execute_bash><execute_ipython>print('Hello World')</execute_ipython>"
    action = agent.step(state, action_str)
    assert not isinstance(action, IPythonRunCellAction)

def test_execute_ipython_first_command(agent, state):
    action_str = "<execute_ipython>print('Hello World')</execute_ipython><execute_bash>echo 'Hello World'</execute_bash>"
    action = agent.step(state, action_str)
    assert isinstance(action, IPythonRunCellAction)
    assert action.code == "print('Hello World')"

def test_execute_browse_first_command(agent, state):
    action_str = "<execute_browse>open('http://example.com')</execute_browse><execute_bash>echo 'Hello World'</execute_bash>"
    action = agent.step(state, action_str)
    assert isinstance(action, BrowseInteractiveAction)
    assert action.browser_actions == "open('http://example.com')"
