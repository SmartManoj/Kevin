import requests
import json
if 1:
    json_data = {
        'feedback_id': '4dbb93310608f43026c9843cf184ce93240b31565f6eb913fbcda369d43ec639',
    }

    response = requests.post(
        'https://show-od-trajectory-3u9bw9tx.uc.gateway.dev/show-od-trajectory',
        json=json_data,
    )

    with open('response.json', 'w') as f:
        data = response.json()
        json.dump(data, f)
else:
    with open('response.json', 'r') as f:
        data = json.load(f)
for i in data['trajectory']:
    if i.get('action') == 'message':
        print(i['args']['content'])
    else:
        print(i)
    print('-'*100)


