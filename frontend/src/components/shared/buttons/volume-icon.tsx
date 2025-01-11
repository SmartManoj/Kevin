import React from "react";
import { IoMdVolumeHigh, IoMdVolumeOff } from "react-icons/io";
import { playAudio } from "#/utils/play-audio";

export function VolumeIcon() {
  const [isMuted, setIsMuted] = React.useState(
    localStorage["is_muted"] === "true",
  );

  const toggleMute = () => {
    const newIsMuted = !isMuted;
    setIsMuted(newIsMuted);
    localStorage["is_muted"] = newIsMuted ? "true" : "false";
    if (!newIsMuted) {
      playAudio("beep.wav");
    }
  };

  return (
    <div
      className="cursor-pointer hover:opacity-80 transition-all"
      onClick={toggleMute}
    >
      {isMuted ? <IoMdVolumeOff size={23} /> : <IoMdVolumeHigh size={23} />}
    </div>
  );
}
