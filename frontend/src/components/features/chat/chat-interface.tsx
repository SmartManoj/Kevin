import { useDispatch, useSelector } from "react-redux";
import React from "react";
import posthog from "posthog-js";
import { useParams } from "react-router";
import { convertImageToBase64 } from "#/utils/convert-image-to-base-64";
import { TrajectoryActions } from "../trajectory/trajectory-actions";
import { createChatMessage, createRegenerateLastMessage } from "#/services/chat-service";
import { InteractiveChatBox } from "./interactive-chat-box";
import { addUserMessage, removeLastAssistantMessage } from "#/state/chat-slice";
import { RootState } from "#/store";
import { AgentState } from "#/types/agent-state";
import { generateAgentStateChangeEvent } from "#/services/agent-state-service";
import { FeedbackModal } from "../feedback/feedback-modal";
import { useScrollToBottom } from "#/hooks/use-scroll-to-bottom";
import { TypingIndicator } from "./typing-indicator";
import { useWsClient } from "#/context/ws-client-provider";
import { Messages } from "./messages";
import { ChatSuggestions } from "./chat-suggestions";
import { ActionSuggestions } from "./action-suggestions";
import { ContinueButton } from "#/components/shared/buttons/continue-button";
import { ScrollToBottomButton } from "#/components/shared/buttons/scroll-to-bottom-button";
import { IoMdChatbubbles } from "react-icons/io";
import { playAudio } from "#/utils/play-audio";
import { I18nKey } from "#/i18n/declaration";
import { useTranslation } from "react-i18next";
import { VolumeIcon } from "#/components/shared/buttons/volume-icon";
import { FaSyncAlt } from "react-icons/fa";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { useGetTrajectory } from "#/hooks/mutation/use-get-trajectory";
import { downloadTrajectory } from "#/utils/download-files";
import { displayErrorToast } from "#/utils/custom-toast-handlers";

function getEntryPoint(
  hasRepository: boolean | null,
  hasImportedProjectZip: boolean | null,
): string {
  if (hasRepository) return "github";
  if (hasImportedProjectZip) return "zip";
  return "direct";
}

export function ChatInterface() {
  const { send, isLoadingMessages } = useWsClient();
  const { t } = useTranslation();
  const dispatch = useDispatch();
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const { scrollDomToBottom, onChatBodyScroll, hitBottom } =
    useScrollToBottom(scrollRef);

  const { messages } = useSelector((state: RootState) => state.chat);
  const { curAgentState } = useSelector((state: RootState) => state.agent);

  const [feedbackPolarity, setFeedbackPolarity] = React.useState<
    "positive" | "negative"
  >("positive");
  const [feedbackModalIsOpen, setFeedbackModalIsOpen] = React.useState(false);
  const [messageToSend, setMessageToSend] = React.useState<string | null>(null);
  const [autoMode, setAutoMode] = React.useState(false);

  const { selectedRepository, importedProjectZip } = useSelector(
    (state: RootState) => state.initialQuery,
  );
  const params = useParams();
  const { mutate: getTrajectory } = useGetTrajectory();

  const handleSendMessage = async (content: string, files: File[]) => {
    if (messages.length === 0) {
      posthog.capture("initial_query_submitted", {
        entry_point: getEntryPoint(
          selectedRepository !== null,
          importedProjectZip !== null,
        ),
        query_character_length: content.length,
        uploaded_zip_size: importedProjectZip?.length,
      });
    } else {
      posthog.capture("user_message_sent", {
        session_message_count: messages.length,
        current_message_length: content.length,
      });
    }
    const promises = files.map((file) => convertImageToBase64(file));
    const imageUrls = await Promise.all(promises);

    const timestamp = new Date().toISOString();
    const pending = true;

    send(createChatMessage(content, imageUrls, timestamp));
    if (content == t(I18nKey.CHAT_INTERFACE$AUTO_MESSAGE)) {
      content = t(I18nKey.CHAT_INTERFACE$AUTO_MESSAGE_SENT);
    }
    dispatch(addUserMessage({ content, imageUrls, timestamp, pending }));
    setMessageToSend(null);
  };

  const handleStop = () => {
    posthog.capture("stop_button_clicked");
    send(generateAgentStateChangeEvent(AgentState.STOPPED));
  };

  const handleSendContinueMsg = () => {
    handleSendMessage("Continue", []);
  };

  const handleAutoMsg = () => {
    handleSendMessage(
      t(I18nKey.CHAT_INTERFACE$AUTO_MESSAGE),
      [],
    );
  };

  const handleRegenerateClick = () => {
    dispatch(removeLastAssistantMessage());
    send(createRegenerateLastMessage());
  };

  const onClickShareFeedbackActionButton = async (
    polarity: "positive" | "negative",
  ) => {
    setFeedbackModalIsOpen(true);
    setFeedbackPolarity(polarity);
  };
  React.useEffect(() => {
    if (autoMode && curAgentState === AgentState.AWAITING_USER_INPUT) {
      handleAutoMsg();
    }
  }, [autoMode, curAgentState]);
  React.useEffect(() => {
    if (
      (!autoMode && curAgentState === AgentState.AWAITING_USER_INPUT) ||
      curAgentState === AgentState.ERROR ||
      curAgentState === AgentState.FINISHED
    ) {
      if (localStorage["is_muted"] !== "true") playAudio("beep.wav");
    }
  }, [curAgentState]);


  const onClickExportTrajectoryButton = () => {
    if (!params.conversationId) {
      displayErrorToast("ConversationId unknown, cannot download trajectory");
      return;
    }

    getTrajectory(params.conversationId, {
      onSuccess: async (data) => {
        await downloadTrajectory(
          params.conversationId ?? "unknown",
          data.trajectory,
        );
      },
      onError: (error) => {
        displayErrorToast(error.message);
      },
    });
  };

  const isWaitingForUserInput =
    curAgentState === AgentState.AWAITING_USER_INPUT ||
    curAgentState === AgentState.FINISHED;

  let chatInterface = (
    <div className="h-full flex flex-col justify-between" style={{ height: "94%" }}>
      {messages.length === 0 && (
        <ChatSuggestions onSuggestionsClick={setMessageToSend} />
      )}

      <div
        ref={scrollRef}
        onScroll={(e) => onChatBodyScroll(e.currentTarget)}
        className="flex flex-col grow overflow-y-auto overflow-x-hidden px-4 pt-4 gap-2"
      >
        {isLoadingMessages && (
          <div className="flex justify-center">
            <LoadingSpinner size="small" />
          </div>
        )}

        {!isLoadingMessages && (
          <Messages
            messages={messages}
            isAwaitingUserConfirmation={
              curAgentState === AgentState.AWAITING_USER_CONFIRMATION
            }
          />
        )}

        {isWaitingForUserInput && (
          <ActionSuggestions
            onSuggestionsClick={(value) =>
              handleSendMessage(value, [])
            }
          />
        )}
      </div>

      <div className="flex flex-col gap-[6px] px-4 pb-4">
        <div className="flex justify-between relative">
          <div className="flex gap-1">
          <TrajectoryActions
            onPositiveFeedback={() =>
              onClickShareFeedbackActionButton("positive")
            }
            onNegativeFeedback={() =>
              onClickShareFeedbackActionButton("negative")
            }
            onExportTrajectory={() => onClickExportTrajectoryButton()}
          />
          <button
              style={{
                width: "25%",
              }}
              type="button"
              onClick={handleRegenerateClick}
              className="p-1 bg-neutral-700 border border-neutral-600 rounded hover:bg-neutral-500"
            >
              <div style={{ top: "-2px", position: "relative" }}>
                {<FaSyncAlt className="inline mr-2 w-3 h-3" />}
              </div>
          </button>
          </div>
          <div className="absolute left-1/2 transform -translate-x-1/2 bottom-0">
            {messages.length > 2 &&
              curAgentState === AgentState.AWAITING_USER_INPUT && (
                <ContinueButton onClick={handleSendContinueMsg} />
              )}
            {curAgentState === AgentState.RUNNING && <TypingIndicator />}
          </div>

          {!hitBottom && <ScrollToBottomButton onClick={scrollDomToBottom} />}
        </div>

        <InteractiveChatBox
          onSubmit={handleSendMessage}
          onStop={handleStop}
          isDisabled={
            curAgentState === AgentState.LOADING ||
            curAgentState === AgentState.AWAITING_USER_CONFIRMATION
          }
          mode={curAgentState === AgentState.RUNNING ? "stop" : "submit"}
          value={messageToSend ?? undefined}
          onChange={setMessageToSend}
        />
      </div>

      <FeedbackModal
        isOpen={feedbackModalIsOpen}
        onClose={() => setFeedbackModalIsOpen(false)}
        polarity={feedbackPolarity}
      />
    </div>
  );
  chatInterface = (
    <div className="flex flex-col h-full bg-neutral-800">
      <div className="flex items-center gap-2 border-b border-neutral-600 text-sm px-4 py-2"
        style={{
          position: "sticky",
          top: "0px",
          zIndex: "10",
          background: "rgb(38 38 38 / var(--tw-bg-opacity))",
        }}
      >
        <IoMdChatbubbles />
        Chat
        <div className="ml-auto">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={autoMode}
              onChange={() => setAutoMode(!autoMode)}
              aria-label="Auto Mode"
          />
          <span>Auto Mode</span>
        </label>
        </div>
        <VolumeIcon />

      </div>
      {chatInterface}
    </div>
  );
  return chatInterface;
}
