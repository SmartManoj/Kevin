import ActionType from "#/types/ActionType";
import Session from "./session";

export function sendChatMessage(message: string, images_urls: string[]): void {
  const event = {
    action: ActionType.MESSAGE,
    args: { content: message, images_urls },
  };
  const eventString = JSON.stringify(event);
  Session.send(eventString);
}

export function regenerateLastMessage(): void {
  const event = {
    action: ActionType.REGENERATE,
    args: {},
  };
  const eventString = JSON.stringify(event);
  Session.send(eventString);
}

export function sendJupyterCode(code: string): void {
  const event = {
    action: ActionType.RUN_IPYTHON,
    args: { code},
  };
  const eventString = JSON.stringify(event);
  Session.send(eventString);
}
