import json
import os
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import litellm
import pip._vendor.tomli as toml
from dotenv import load_dotenv

load_dotenv()
with open('config.toml', 'r') as f:
    config = toml.load(f)
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

args, kwargs = json.load(open("logs/llm/request.json"))

response = litellm.completion(
    model=model,
    api_key=api_key,
    seed=seed,
    temperature=temperature,
    *args,
    **kwargs,
)

print(response.choices[0].message.content)
# print(response)
