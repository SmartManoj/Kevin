import React, { useState } from "react";
import { useSelector } from "react-redux";
import { RootState } from "#/store";
import { updateBrowserTabUrl } from "#/services/browse-service";
import { BrowserSnapshot } from "./browser-snapshot";
import { EmptyBrowserMessage } from "./empty-browser-message";
import { useWsClient } from "#/context/ws-client-provider";

export function BrowserPanel() {
  const { send } = useWsClient();
  const { url, screenshotSrc } = useSelector(
    (state: RootState) => state.browser,
  );

  const [editableUrl, setEditableUrl] = useState(url);

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEditableUrl(e.target.value);
  };

  const handleURLBar = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      send(updateBrowserTabUrl(editableUrl));
    }
  };

  const imgSrc =
    screenshotSrc && screenshotSrc.startsWith("data:image/png;base64,")
      ? screenshotSrc
      : `data:image/png;base64,${screenshotSrc || ""}`;

  return (
    <div className="h-full w-full flex flex-col text-neutral-400">
      <div className="w-full p-2 truncate border-b border-neutral-600">
        <input
          type="text"
          value={editableUrl}
          onChange={handleUrlChange}
          onKeyDown={handleURLBar}
          className="w-full bg-transparent border-none outline-none text-neutral-400"
        />
      </div>
      <div className="overflow-y-auto grow scrollbar-hide rounded-xl">
        {screenshotSrc ? (
          <BrowserSnapshot src={imgSrc} />
        ) : (
          <EmptyBrowserMessage />
        )}
      </div>
    </div>
  );
}
