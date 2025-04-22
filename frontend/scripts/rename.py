f=r'frontend\src\i18n\translation.json'

import json

with open(f, 'r', encoding='utf-8') as file:
    data = json.load(file, strict=False)

if 1:
    for key, value in data.items():
        if 'OpenHands' in value['en']:
            data[key]['en'] = value['en'].replace('OpenHands', 'Kevin')

with open(f, 'w', encoding='utf-8') as file:
    json.dump(data, file, indent=4, ensure_ascii=False)
