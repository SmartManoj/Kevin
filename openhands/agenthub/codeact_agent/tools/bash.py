from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk

_BASH_DESCRIPTION = """**Bash Command Execution in Persistent Shell**  

- **One command at a time**: Use `&&` or `;` for sequential execution.  
- **Persistent session**: Environment, working directory, and variables persist.  
- **Timeout**: Commands auto-stop after 120s unless continued.  

**Running & Interacting with Processes**  
- **Long-running commands**: Run in the background, e.g., `python3 app.py > server.log 2>&1 &`.  
- **Interact with running processes**: If exit code `-1`, send input or control commands (`C-c`, `C-d`, `C-z`).  

**Best Practices**  
- **Verify directories** before creating files.  
- **Use absolute paths** to maintain working directory.  

**Output Handling**  
- **Truncation**: Large outputs get truncated.
"""

CmdRunTool = ChatCompletionToolParam(
    type='function',
    function=ChatCompletionToolParamFunctionChunk(
        name='execute_bash',
        description=_BASH_DESCRIPTION,
        parameters={
            'type': 'object',
            'properties': {
                'command': {
                    'type': 'string',
                    'description': 'The bash command to execute. Can be empty string to view additional logs when previous exit code is `-1`. Can be `C-c` (Ctrl+C) to interrupt the currently running process. Note: You can only execute one bash command at a time. If you need to run multiple commands sequentially, you can use `&&` or `;` to chain them together.',
                },
                'is_input': {
                    'type': 'string',
                    'description': 'If True, the command is an input to the running process. If False, the command is a bash command to be executed in the terminal. Default is False.',
                    'enum': ['true', 'false'],
                },
            },
            'required': ['command'],
        },
    ),
)
