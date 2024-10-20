import ActionType from "#/types/ActionType";

export function getTerminalCommand(command: string, hidden: boolean = false) {
  // replace ^c character when copied from terminal
  // eslint-disable-next-line no-control-regex
  const cleanedCommand = command.replace(/\u0003\b/, "");
  const event = { action: ActionType.RUN, args: { command: cleanedCommand, hidden } };
  return JSON.stringify(event);
}

export function getGitHubTokenCommand(gitHubToken: string) {
  const command = `export GITHUB_TOKEN=${gitHubToken}`;
  const event = getTerminalCommand(command, true);
  return event;
}

export function getCloneRepoCommand(gitHubToken: string, repository: string) {
  const url = `https://${gitHubToken}@github.com/${repository}.git`;
  const dirName = repository.split("/")[1];
  const command = `git clone ${url} ${dirName} ; cd ${dirName} ; git checkout -b openhands-workspace`;
  const event = getTerminalCommand(command, true);
  return event;
}
