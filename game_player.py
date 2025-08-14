import os
# MAX_ITERATIONS = 500
MAX_ITERATIONS = 1

for _ in range(MAX_ITERATIONS):
    # run game data fetcher
    os.system('python3 workspace/games/game_data_fetcher.py')

    # run agent
    prompt = '''
SYSTEM: ARC-3 OpenHands Orchestrator

You are an ARC Prize 3 game player who plans and executes transformations using a domain-specific language (DSL) the user already designed in /workspace/ARC-Tools directory.

Inputs available each step
- files:
  - /workspace/games/available_actions.json
  - /workspace/games/grid_{step_number}.json
  - /workspace/games/grid_{step_number}.png
  - /workspace/games/current_step.txt

Reference solutions of other games are in ls20, vc33, ft09.py in /workspace/games/reference_solutions.
Solution guide for ls20 is in ls20_solution.md.

TASK:
Using these information, you need to plan and execute the next action correctly (visualize the png and use python to analyse the json).
Using game_handler.py (client), you can execute actions. (server is already running by the game administrator)
Save your current summary to /workspace/games/summary.txt.

Don't edit reference_solutons folder. Use <execute_ipython> to execute python code.


'''
    with open('prompt.txt', 'w') as f:
        f.write(prompt)
    os.environ['DEBUG'] = '1'
    cmd = f"poetry run python -m openhands.core.main -t '{prompt}'"
    os.system(cmd)

from pymsgbox import alert
alert('agent done')
