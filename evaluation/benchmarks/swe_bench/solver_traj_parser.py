import json
from pprint import pprint
import boto3
import os

# Initialize the S3 client
s3 = boto3.client('s3')

# Parse the S3 path
s3_path = 's3://swe-bench-experiments/verified/20241028_solver/trajs/matplotlib__matplotlib-23476.json'
bucket_name = s3_path.split('/')[2]
object_key = '/'.join(s3_path.split('/')[3:])
# Fetch the object
response = s3.get_object(Bucket=bucket_name, Key=object_key)

# Read the content
content = response['Body'].read().decode('utf-8')  # Adjust decoding as needed
# messages = json.loads(content)
messages = content
step_count = 0
print(messages)
exit()
for message in messages:
    if message['role'] == 'assistant':
        step_count += 1
        print(f'Step {step_count}:')
    role = message['role']
    content = message['content']
    print(f'{role}:', content)
    if message['role'] == 'assistant':
        tool_calls = message.get('tool_calls', [])
        if tool_calls:
            print('=' * 10)

        for tool_call in tool_calls:
            arguments = tool_call['function']['arguments']
            arguments = json.loads(arguments)
            for k, v in arguments.items():
                print(f'{k}: {v}')
    print('='*100)
