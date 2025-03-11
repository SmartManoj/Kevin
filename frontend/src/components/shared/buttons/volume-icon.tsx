import React from "react";
import { IoMdVolumeHigh, IoMdVolumeOff } from "react-icons/io";
import { RiChatVoiceFill, RiUserVoiceFill  } from "react-icons/ri";
import { playAudio } from "#/utils/play-audio";
import notificationSound from "#/assets/notification.mp3";

export function VoiceModeIcon() {
  const [isVoiceMode, setIsVoiceMode] = React.useState(
    localStorage["voiceMode"] === "true",
  );

  const toggleVoiceMode = () => {
    if (speechSynthesis.speaking) {
      speechSynthesis.cancel();
    }
    const newIsVoiceMode = !isVoiceMode;
    setIsVoiceMode(newIsVoiceMode);
    localStorage["voiceMode"] = newIsVoiceMode ? "true" : "false";
  };

  return (
    <div
      className="cursor-pointer hover:opacity-80 transition-all"
      onClick={toggleVoiceMode}
    >
      {!isVoiceMode ? <RiUserVoiceFill size={23} /> : <RiUserVoiceFill size={23} style={{ color: "orange" }}/>}
    </div>
  );
}

export function VolumeIcon() {
  const [isMuted, setIsMuted] = React.useState(
    localStorage["is_muted"] === "true",
  );

  const toggleMute = () => {
    const newIsMuted = !isMuted;
    setIsMuted(newIsMuted);
    localStorage["is_muted"] = newIsMuted ? "true" : "false";
    if (!newIsMuted) {
      playAudio(notificationSound);
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
