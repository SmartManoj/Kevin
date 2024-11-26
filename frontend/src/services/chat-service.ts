import ActionType from "#/types/action-type";

export function createChatMessage(
  message: string,
  image_urls: string[],
  timestamp: string,
) {
  const event = {
    action: ActionType.MESSAGE,
    args: { content: message, image_urls, timestamp },
  };
  return event;
}

export function createRegenerateLastMessage() {
  const event = {
    action: ActionType.REGENERATE,
    args: {},
  };
  return event;
}

export function createJupyterCode(code: string) {
  const event = {
    action: ActionType.RUN_IPYTHON,
    args: { code },
  };
  return event;
}
