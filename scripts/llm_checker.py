import os
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import litellm
import tomllib
from dotenv import load_dotenv

load_dotenv()
with open('config.toml', 'rb') as f:
    config = tomllib.load(f)
    config = config['llm']
    group = 'gemini_pro'
    group = 'gemini_exp'
    # group = 'gemini'
    # group = 'nemo'
    group = 'or'
    group = 'groq'
    group = 'ollama'
    group = 'hv'
    # group = ''
    if group in config:
        config = config[group]

model = config['model']
print('Using model:', model)
api_key = config.get('api_key')
base_url = config.get('base_url')
args = (
    {
        'base_url': base_url,
    }
    if base_url
    else {}
)
if base_url and model.startswith('ollama'):
    os.environ['OLLAMA_API_BASE'] = base_url
has_vision = litellm.supports_vision(model)
if has_vision:
    print('Model supports vision')
else:
    print('Model does not support vision')
response = litellm.completion(
    model=model,
    messages=[{'role': 'user', 'content': 'Hello, how are you?'}],
    api_key=api_key,
    **args,
)

print(response.choices[0].message.content)
