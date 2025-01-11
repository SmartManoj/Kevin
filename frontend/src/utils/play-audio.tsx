export const playAudio = (audioFile: string) => {
  const snd = new Audio(`/${audioFile}`);
  snd.addEventListener("canplaythrough", () => snd.play());
};
