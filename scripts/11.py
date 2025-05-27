import elevenlabs
import os
from dotenv import load_dotenv
load_dotenv()

client = elevenlabs.ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))
voice = 'Ramaa - Expert Tamil Book Narrator'
# add the voice to the library
voiceId = "jsxww9ngE2fwXHlkWgkm"
a=client.voices.get(voiceId)
print(a)
# a=client.voices.get_shared(search=voice).voices[0]
# print(a.voice_id)
# client.voices.add_sharing_voice(voice_id=a.voice_id,new_name=voice, public_user_id=a.public_owner_id)
text = "ஏண்டா, இந்த ஜாவா கோடு எல்லாம் பாத்தா, ஒரு மாதிரி கடுப்பாவுதுல, சும்மா ஒரு சின்ன விஷயத்துக்கு கூட இம்புட்டு பில்டப்பா?";

audio = client.generate(text=text, voice=voice,model="eleven_turbo_v2_5")
elevenlabs.save(audio, 'mind_voice.mp3')

import os
# ffplay mind_voice.mp3
os.system('ffplay mind_voice.mp3 -autoexit -nodisp')
