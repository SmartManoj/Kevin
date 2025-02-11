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
    group = config.get('use_group')
    if group in config:
        config.update(config[group])


model = config['model']
print('Using model:', model)
api_key = config.get('api_key')
base_url = config.get('base_url')
print('Using base_url:', base_url)
seed = config.get('seed', 42)
temperature = config.get('temperature', 0)
print('Using temperature:', temperature, 'and seed:', seed)
print('-' * 100)
args = (
    {
        'base_url': base_url,
    }
    if base_url
    else {}
)
if base_url and model.startswith('ollama'):
    os.environ['OLLAMA_API_BASE'] = base_url
if 0:
    has_vision = litellm.supports_vision(model)
    if has_vision:
        print('Model supports vision')
    else:
        print('Model does not support vision')
response = litellm.completion(
    model=model,
    messages=[{'role': 'user', 'content': 'Tell a random number with 4 decimal places between 1 to 10.'}],
    api_key=api_key,
    **args,
    seed=seed,
    temperature=temperature,
)

print(response.choices[0].message.content)
# print(response)
