import ActionType from "#/types/action-type";

export function updateBrowserTabUrl(newUrl: string) {
  const event = { action: ActionType.BROWSE, args: { url: newUrl } };
  return event;
}
