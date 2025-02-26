import os
import pickle
from pprint import pprint

import toml
from datasets import load_dataset

from evaluation.benchmarks.swe_bench.swe_bench2 import update_issue_description

os.environ['SANDBOX_PORT'] = '63712'

from sandbox_checker import execute_action, run, run_ipython

with open(r'evaluation\benchmarks\swe_bench\config.toml', 'r') as f:
    config = toml.load(f)

import re


def count_hunks_from_patch(patch):
    hunk_pattern = re.compile(r'^@@.*@@', re.MULTILINE)
    hunk_count = len(hunk_pattern.findall(patch))
    return hunk_count


# print(config)
# instance_id = 'astropy__astropy-14539'
def validate_instance_id(instance_id):
    regex = r'^[a-zA-Z0-9]+__[a-zA-Z0-9]+-[0-9]+$'
    if not re.match(regex, instance_id):
        return False
    return True

go = 1
if go:
    from pyperclip import paste
    instance_id = paste()
    if not validate_instance_id(instance_id):
        instance_id = None

if not instance_id:
    go = 0
    instance_id = config['selected_ids'][0]
repo, issue_id = instance_id.rsplit('-', 1)
repo = repo.replace('__', '/')
url = f'https://github.com/{repo}/pull/{issue_id}'
print(url)
if go:
    import webbrowser
    webbrowser.open(url)
    exit()

dataset_path='princeton-nlp/SWE-bench_Full'
dataset_path='C:/Users/smart/Desktop/UO/K/konwinski-prize/data/data.parquet'

def get_instance(instance_id):
    force = 0
    for _ in range(2):
        if not os.path.exists('./cache/filtered_data.pkl') or force:
            kwargs = {
                'cache_dir': './cache',
                'verification_mode': 'no_checks',
                'num_proc': 4,
            }
            if 'parquet' in dataset_path:
                dataset = load_dataset('parquet', data_files=dataset_path, split='train', ** kwargs)
            else:
                dataset = load_dataset(dataset_path, split='test', ** kwargs)

            # Serialize filtered dataset
            ins = dataset.filter(lambda x: x['instance_id'] == instance_id)
            with open('./cache/filtered_data.pkl', 'wb') as f:
                pickle.dump(ins, f)
            break
        else:
            with open('./cache/filtered_data.pkl', 'rb') as f:
                ins = pickle.load(f)
        if instance_id != ins['instance_id'][0]:
            print(ins['instance_id'], 'new ->', instance_id)
            force = 1
    return ins


if 0:
    instance_ids = [
        'django__django-13033',
        'django__django-13158',
        'django__django-13590',
        'django__django-14017',
        'django__django-14580',
        'django__django-14608',
        'django__django-14787',
        'matplotlib__matplotlib-24149',
        'sympy__sympy-12419',
        'sympy__sympy-16792',
        'sympy__sympy-17655',
    ]
    for instance_id in instance_ids:
        ins = get_instance(instance_id)
        print(instance_id, count_hunks_from_patch(ins['patch'][0]))
    exit()
else:
    ins = get_instance(instance_id)
#
print('base_commit', ins['base_commit'])
# print('environment_setup_commit', ins['environment_setup_commit'])
# print('Hints', ins['hints_text'])

print(['problem_statement'])
# print(ins['problem_statement'][0])
a = update_issue_description(ins['problem_statement'][0], instance_id)
print(a)
if 1:
    print('-' * 100)
    test_patch = ins['test_patch'][0]
    patch = ins['patch'][0]
    if 1:
        print(patch)
        code = rf"""
code = r'''{patch}'''
with open(f'/testbed/patch.diff', 'w') as f:
    f.write(code)
"""
        execute_action(run_ipython(code))
        cmd = 'git apply /testbed/patch.diff'
        execute_action(run(cmd))

    if 0:
        print(test_patch)
        code = rf"""
code = r'''{test_patch}'''
with open(f'/testbed/test_patch.diff', 'w') as f:
    f.write(code)
"""
        execute_action(run_ipython(code))
        cmd = 'git apply /testbed/test_patch.diff'
        execute_action(run(cmd))


if 0:
    print('-' * 100)
    print(['TEST PASS_TO_PASS'])
    pprint(ins['PASS_TO_PASS'][0])
    print(['TEST FAIL_TO_PASS'])
    print(ins['FAIL_TO_PASS'][0])
