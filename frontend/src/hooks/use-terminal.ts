import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import React from "react";
import { Command } from "#/state/command-slice";
import { getTerminalCommand } from "#/services/terminal-service";
import { parseTerminalOutput } from "#/utils/parse-terminal-output";
import { useWsClient } from "#/context/ws-client-provider";

/*
  NOTE: Tests for this hook are indirectly covered by the tests for the XTermTerminal component.
  The reason for this is that the hook exposes a ref that requires a DOM element to be rendered.
*/

interface UseTerminalConfig {
  commands: Command[];
  secrets: string[];
  disabled: boolean;
}

const DEFAULT_TERMINAL_CONFIG: UseTerminalConfig = {
  commands: [],
  secrets: [],
  disabled: false,
};

export const useTerminal = ({
  commands,
  secrets,
  disabled,
}: UseTerminalConfig = DEFAULT_TERMINAL_CONFIG) => {
  const { send } = useWsClient();
  const terminal = React.useRef<Terminal | null>(null);
  const fitAddon = React.useRef<FitAddon | null>(null);
  const ref = React.useRef<HTMLDivElement>(null);
  const lastCommandIndex = React.useRef(0);
  const lastCommand = React.useRef("");
  const keyEventDisposable = React.useRef<{ dispose: () => void } | null>(null);

  const commandHistory = React.useRef<string[]>([]);
  const currentCommandIndex = React.useRef<number>(-1);
  const createTerminal = () =>
    new Terminal({
      fontFamily: "Menlo, Monaco, 'Courier New', monospace",
      fontSize: 14,
      theme: {
        background: "#24272E",
      },
    });

  const initializeTerminal = () => {
    if (terminal.current) {
      if (fitAddon.current) terminal.current.loadAddon(fitAddon.current);
      if (ref.current) terminal.current.open(ref.current);
    }
  };

  const copySelection = (selection: string) => {
    const clipboardItem = new ClipboardItem({
      "text/plain": new Blob([selection], { type: "text/plain" }),
    });

    navigator.clipboard.write([clipboardItem]);
  };

  const pasteSelection = (callback: (text: string) => void) => {
    navigator.clipboard.readText().then(callback);
  };

  const pasteHandler = (event: KeyboardEvent, cb: (text: string) => void) => {
    // if (
    //   (arg.ctrlKey || arg.metaKey) &&
    //   arg.code === "KeyC" &&
    //   arg.type === "keydown"
    // ) {
    //   sendTerminalCommand("\x03");
    // }
    const isControlOrMetaPressed =
      event.type === "keydown" && (event.ctrlKey || event.metaKey);

    if (isControlOrMetaPressed) {
      if (event.code === "KeyV") {
        pasteSelection((text: string) => {
          terminal.current?.write(text);
          cb(text);
        });
      }

      if (event.code === "KeyC") {
        const selection = terminal.current?.getSelection();
        if (selection) copySelection(selection);
      }
    }

    return true;
  };

  const handleBackspace = (command: string) => {
    terminal.current?.write("\b \b");
    return command.slice(0, -1);
  };

  React.useEffect(() => {
    /* Create a new terminal instance */
    terminal.current = createTerminal();
    fitAddon.current = new FitAddon();

    let resizeObserver: ResizeObserver | null = null;
    
    if (ref.current) {
      /* Initialize the terminal in the DOM */
      initializeTerminal();

      terminal.current.write("kevin@kevin-workspace:/workspace $ ");
      /* Listen for resize events */
      resizeObserver = new ResizeObserver(() => {
        fitAddon.current?.fit();
      });
      resizeObserver.observe(ref.current);
    }

    return () => {
      terminal.current?.dispose();
      resizeObserver?.disconnect();
    };
  }, []);

  React.useEffect(() => {
    /* Write commands to the terminal */
    if (terminal.current && commands.length > 0) {
      // commands would be cleared. Reset the last command index
      if (lastCommandIndex.current >= commands.length) {
        lastCommandIndex.current = 0;
        terminal.current?.clear();
      }
      // Start writing commands from the last command index
      for (let i = lastCommandIndex.current; i < commands.length; i += 1) {
        // eslint-disable-next-line prefer-const
        let { content, type } = commands[i];
        secrets.forEach((secret) => {
          content = content.replaceAll(secret, "*".repeat(10));
        });

        terminal.current?.writeln(
          parseTerminalOutput(content.replaceAll("\n", "\r\n").trim()),
        );

        if (type === "output") {
          terminal.current.write(`\n$ `);
        }
      }

      lastCommandIndex.current = commands.length; // Update the position of the last command
    }
  }, [commands]);

  const clearTerminal = () => {
    terminal.current?.clear();
  };

  
  React.useEffect(() => {
    if (terminal.current) {
      // Dispose of existing listeners if they exist
      if (keyEventDisposable.current) {
        keyEventDisposable.current.dispose();
        keyEventDisposable.current = null;
      }

      let commandBuffer = "";
      const handleContextMenu = (e: MouseEvent) => {
        e.preventDefault();
        navigator.clipboard.readText().then((text) => {
          terminal.current?.write(text);
          commandBuffer += text;
        });
      };
  
      const handleEnter = (command: string) => {
        terminal.current?.write("\r\n");
        // replace ^c character when copied from terminal
        // eslint-disable-next-line no-control-regex
        const cleanedCommand = command.replace(/\u0003\b/, "");
        if (cleanedCommand.trim() === "") return;
        send(getTerminalCommand(cleanedCommand));
        //  Update command history using previous state
        commandHistory.current = [...commandHistory.current, cleanedCommand];
        currentCommandIndex.current = -1;
      };
      const handleUpArrow = (e: KeyboardEvent) => {
        e.preventDefault();
        if (commandHistory.current.length === 0) return;
        const newIndex = currentCommandIndex.current === -1 ? commandHistory.current.length - 1 : Math.max(currentCommandIndex.current - 1, 0);
        const command = commandHistory.current[newIndex];
        const to_be_written = `${'\b \b'.repeat(commandBuffer.length)}${command}`
        terminal.current?.write(to_be_written);
        commandBuffer = command;
        currentCommandIndex.current = newIndex;
      };
      const handleDownArrow = (e: KeyboardEvent) => {
        e.preventDefault();
        if (commandHistory.current.length === 0) return;
        const newIndex = currentCommandIndex.current === -1 ? commandHistory.current.length - 1 : Math.min(currentCommandIndex.current + 1, commandHistory.current.length - 1);
        const command = commandHistory.current[newIndex];
        const to_be_written = `${'\b \b'.repeat(commandBuffer.length)}${command}`
        terminal.current?.write(to_be_written);
        commandBuffer = command;
        currentCommandIndex.current = newIndex;
      };
    const terminalElement = terminal.current?.element;

      if (terminalElement) {
        // right click to paste
        terminalElement.addEventListener("contextmenu", handleContextMenu);
      }
      if (!disabled) {
        // Add new key event listener and store the disposable
        keyEventDisposable.current = terminal.current.onKey(({ key, domEvent }) => {
          if (domEvent.key === "Enter") {
            lastCommand.current = commandBuffer;
            handleEnter(commandBuffer);
            commandBuffer = "";
          } else if (domEvent.key === "Tab") {
            // do nothing
          } else if (domEvent.key === "Backspace") {
            if (commandBuffer.length > 0) {
              commandBuffer = handleBackspace(commandBuffer);
            }
          } else if (domEvent.key === "ArrowUp") {
            handleUpArrow(domEvent);
          } else if (domEvent.key === "ArrowDown") {
            handleDownArrow(domEvent);
          } else {
            // Ignore paste event
            if (key.charCodeAt(0) === 22) {
              return;
            }
            commandBuffer += key;
            terminal.current?.write(key);
          }
        });
        terminal.current.attachCustomKeyEventHandler((event) =>
          pasteHandler(event, (text) => {
            commandBuffer += text;
          }),
        );
      } else {
        // Add a noop handler when disabled
        keyEventDisposable.current = terminal.current.onKey((e) => {
          e.domEvent.preventDefault();
          e.domEvent.stopPropagation();
        });
      }
    }

    return () => {
      if (keyEventDisposable.current) {
        keyEventDisposable.current.dispose();
        keyEventDisposable.current = null;
      }
    };
  }, [disabled]);

  return { ref, clearTerminal };
};
