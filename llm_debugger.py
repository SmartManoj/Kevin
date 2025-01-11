#! /usr/bin/env python3.11
import litellm
import toml

number = 1
model = 'gemini_pro'
model = 'gemini_flash'
model = 'groq'
with open('evaluation/benchmarks/swe_bench/config.toml', 'r') as f:
    environ = f.read()
    config = toml.loads(environ)
    selection_id = config['selected_ids'][0].split('-')[-1]
folder = f'{model}_{selection_id}'
# folder = 'default'
prompt = f'logs/llm/{folder}/{number:03d}_prompt.log'
response = f'logs/llm/{folder}/{number:03d}_response.log'

with open(prompt, 'r') as file:
    prompt_content = file.read()

with open(response, 'r') as file:
    response_content = file.read()

config = 'config.toml'

with open(config, 'r') as file:
    config_content = toml.load(file)['llm']
    eval = 1
    if eval:
        config_content = config_content[model]


model = config_content['model']
api_key = config_content['api_key']

question = 'Why did you use insert content before line 60?'
question = 'Why are you searching for header_rows?'
question = 'Why did you search for header_rows in ui.py?'
question = '''
why not passed string to search_class?
'''
inst = '\n\nJust tell only the reason for your action.'
inst = f'give analysis; then give Step {number}: and produce the solution along with thought process.'
question += inst
new_prompt = f"""
INITIAL PROMPT:

{prompt_content}

INITIAL RESPONSE:
{response_content}

DEBUGGER:
{question}
"""
messages = [
    {
        'role': 'system',
        'content': 'You are the assistant. Your responses are wrong. The debugger will ask you questions and provide you with the initial prompt abd initial response. Answer the questions and provide the corrected response.',
    },
    {'role': 'user', 'content': new_prompt},
]

while True:
    response = litellm.completion(
        model=model,
        messages=messages,
        api_key=api_key,
    )
    resp = response['choices'][0]['message']['content']
    print(resp)
    question = input('> ')

    if question == 'q':
        with open(prompt, 'r') as file:
            prompt_content = file.read()
        response = litellm.completion(
            model=model,
            messages=[{'role': 'user', 'content': prompt_content}],
            api_key=api_key,
        )
        resp = response['choices'][0]['message']['content']
        print(resp)
        break
    messages.append({'role': 'assistant', 'content': 'Assistant: ' + resp})
    messages.append({'role': 'user', 'content': 'User: ' + question})
    inst = 'Reply in one line.'
    messages.append({'role': 'system', 'content': 'System: ' + inst})
