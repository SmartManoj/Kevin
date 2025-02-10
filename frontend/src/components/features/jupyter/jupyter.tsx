import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { RootState } from "#/store";
import { useScrollToBottom } from "#/hooks/use-scroll-to-bottom";
import { JupyterCell } from "./jupyter-cell";
import { ScrollToBottomButton } from "#/components/shared/buttons/scroll-to-bottom-button";
import { useWsClient } from "#/context/ws-client-provider";
import { VscArrowUp } from "react-icons/vsc";
import { Textarea } from "@heroui/react";
import { appendJupyterInput } from "#/state/jupyter-slice";
import { createJupyterCode } from "#/services/chat-service";

interface JupyterEditorProps {
  maxWidth: number;
}

export function JupyterEditor({ maxWidth }: JupyterEditorProps) {
  const dispatch = useDispatch();
  const { send } = useWsClient();
  const cells = useSelector((state: RootState) => state.jupyter?.cells ?? []);
  const jupyterRef = React.useRef<HTMLDivElement>(null);

  const { hitBottom, scrollDomToBottom, onChatBodyScroll } =
    useScrollToBottom(jupyterRef);
  const [inputValue, setInputValue] = React.useState("");

  const handleInputSubmit = () => {
    if (inputValue.trim()) {
      send(createJupyterCode(inputValue));
      setInputValue("");
    }
  };
  const onKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault(); // prevent a new line
      handleInputSubmit();
    }
  };
  let jupyterEditor = (
    <div className="flex-1 h-full flex flex-col" style={{ maxWidth, height: "85%" }}>
      <div
        data-testid="jupyter-container"
        className="flex-1 overflow-y-auto max-h-[85%]"
        ref={jupyterRef}
        onScroll={(e) => onChatBodyScroll(e.currentTarget)}
      >
        {cells.map((cell, index) => (
          <JupyterCell key={index} cell={cell} />
        ))}
      </div>
      {!hitBottom && (
        <div className="sticky bottom-2 flex items-center justify-center">
          <ScrollToBottomButton onClick={scrollDomToBottom} />
        </div>
      )}
    </div>
  );
  jupyterEditor = (
    <div className="JupyterEditor" style={{ height: "100%", position: "relative" }}>
      {jupyterEditor}
      <div
        className="sticky bottom-0 flex p-1 "
        onKeyDown={onKeyPress}
        style={{ bottom: 0, position: "sticky", width: "100%" }}
      >
        <Textarea
          value={inputValue}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setInputValue(e.target.value)}
          onKeyDown={onKeyPress}
          placeholder="Enter Python code here..."
          className="p-1"
          classNames={{
            inputWrapper: "bg-neutral-700 border border-neutral-600 rounded-lg",
            input: "pr-16 text-neutral-400",
          }}
          maxRows={10}
          minRows={1}
          variant="bordered"
        />
        <button
          type="button"
          onClick={handleInputSubmit}
          className="p-2 bg-blue-600 text-white rounded-r"
          aria-label="Run"
        >
          <VscArrowUp size={25} />
        </button>
      </div>
    </div>
  );
  return jupyterEditor;
}
