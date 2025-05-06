f=r'frontend\src\i18n\translation.json'

from hashlib import scrypt
import json

with open(f, 'r', encoding='utf-8') as file:
    data = json.load(file, strict=False)

if 1:
    for key, value in data.items():
        if 'OpenHands' in value['en']:
            data[key]['en'] = value['en'].replace('OpenHands', 'Kevin')
data['CHAT_INTERFACE$AUTO_MESSAGE'] = { 'en': "You have full access to this system. Please continue working on the task on whatever approach you think is suitable.\nIf you think you have solved the task, you can give <finish> to end the interaction.\nIMPORTANT: YOU SHOULD NEVER ASK FOR HUMAN HELP.\n"}
data['CHAT_INTERFACE$AUTO_MESSAGE_SENT'] = { 'en': "Sent the default Auto Msg 🤖"}
data['PAYMENT$MANAGE_CREDITS']['en'] = "Available Agent Time"


with open(f, 'w', encoding='utf-8', newline='') as file:
    file.write(json.dumps(data, indent=4, ensure_ascii=False))
    file.write('\n')
