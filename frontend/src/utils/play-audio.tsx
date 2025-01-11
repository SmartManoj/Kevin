export const playAudio = (audioFile: string) => {
  const snd = new Audio(`/${audioFile}`);
  snd.addEventListener("canplaythrough", () => snd.play());
};


export const generateAudio = async (text:string) => {
    const ELEVENLABS_API_KEY= localStorage.getItem('ELEVENLABS_API_KEY');
    const voiceId = localStorage.getItem('voiceId') || "9BWtsMINqrJLrRacOk9x"; 
    const apiKey = ELEVENLABS_API_KEY;
    const url = `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`;

    const requestBody = {
        text,
        model_id: "eleven_turbo_v2_5"
        
    };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'xi-api-key': `${apiKey}`,
            },
            body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }

        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);

        const audio = new Audio(audioUrl);
        audio.playbackRate = + (localStorage.getItem('AUDIO_SPEED') || 1.25);
        audio.play();
    } catch (error) {
        console.error('Failed to generate audio:', error);
    }
};

