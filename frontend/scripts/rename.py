f=r'frontend\src\i18n\translation.json'

from hashlib import scrypt
import json
import re
def replace_keep_case(word, replacement, text):
    def func(match):
        g = match.group()
        if g.islower(): return replacement.lower()
        if g.istitle(): return replacement.title()
        if g.isupper(): return replacement.upper()
        return replacement      
    return re.sub(word, func, text, flags=re.I)

with open(f, 'r', encoding='utf-8') as file:
    data = json.load(file, strict=False)

if 1:
    for key, value in data.items():
        if 'openhands' in value['en'].lower():
            data[key]['en'] = replace_keep_case('OpenHands', 'Kevin', value['en'])
data['CHAT_INTERFACE$AUTO_MESSAGE'] = { 'en': "You have full access to this system. Please continue working on the task on whatever approach you think is suitable.\nIf you think you have solved the task, you can give <finish> to end the interaction.\nIMPORTANT: YOU SHOULD NEVER ASK FOR HUMAN HELP.\n"}
data['CHAT_INTERFACE$AUTO_MESSAGE_SENT'] = { 'en': "Sent the default Auto Msg 🤖"}
data['PAYMENT$MANAGE_CREDITS']['en'] = "Available Agent Time"


with open(f, 'w', encoding='utf-8', newline='') as file:
    file.write(json.dumps(data, indent=4, ensure_ascii=False))
    file.write('\n')
