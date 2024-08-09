diffs = r"""
-[{"source": "agent", "action": "run", "args": {"command": "git status", "thought": "", "keep_prompt": true, "is_confirmed": "confirmed"}}, {"source": "agent", "observation": "run", "content": "fatal: not a git repository (or any parent up to mount point /)\r\nStopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).\r\n\r\nopendevin@docker-desktop:/workspace $ ", "extras": {"command_id": -1, "command": "git status", "exit_code": 128}}, {"source": "agent", "observation": "error", "content": "action={'action': 'reject', 'args': {'reason': 'Not a valid git repository.'}} has the wrong arguments", "extras": {}}]
+[{"source": "agent", "action": "run", "args": {"command": "git status", "thought": "", "keep_prompt": true, "is_confirmed": "confirmed"}}, {"source": "agent", "observation": "run", "content": "fatal: not a git repository (or any parent up to mount point /)\r\nStopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).\r\n\r\nopendevin@fv-az1245-968:/workspace $ ", "extras": {"command_id": -1, "command": "git status", "exit_code": 128}}, {"source": "agent", "observation": "error", "content": "Error creating <class 'opendevin.events.action.agent.AgentRejectAction'> from action={'action': 'reject', 'args': {'reason': 'Not a valid git repository.'}}: AgentRejectAction.__init__() got an unexpected keyword argument 'reason'", "extras": {}}]
""".strip().splitlines()

test_patces = {'': ''}
for i in range(0, len(diffs), 2):
    test_patces[diffs[i][1:]] = diffs[i + 1][1:]
print(test_patces)
