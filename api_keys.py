api_keys = []

import os
from dotenv import load_dotenv

load_dotenv()
i = 1
while True:
    key = os.getenv(f'API_KEY_{i}')
    if key:
        api_keys.append(key)
        i += 1
    else:
        break


