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
}

const DEFAULT_TERMINAL_CONFIG: UseTerminalConfig = {
  commands: [],
};

const renderCommand = (command: Command, terminal: Terminal) => {
  const { content, type } = command;

  if (type === "input") {
    terminal.write("$ ");
    terminal.writeln(
      parseTerminalOutput(content.replaceAll("\n", "\r\n").trim()),
    );
  } else {
    terminal.write(`\n`);
    terminal.writeln(
      parseTerminalOutput(content.replaceAll("\n", "\r\n").trim()),
    );
    terminal.write(`\n`);
  }
};

// Create a persistent reference that survives component unmounts
// This ensures terminal history is preserved when navigating away and back
const persistentLastCommandIndex = { current: 0 };

export const useTerminal = ({
  commands,
}: UseTerminalConfig = DEFAULT_TERMINAL_CONFIG) => {
  const { send } = useWsClient();
  const terminal = React.useRef<Terminal | null>(null);
  const fitAddon = React.useRef<FitAddon | null>(null);
  const ref = React.useRef<HTMLDivElement>(null);
  const lastCommandIndex = persistentLastCommandIndex; // Use the persistent reference
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
    terminal.current = createTerminal();
    fitAddon.current = new FitAddon();

    
    if (ref.current) {
      initializeTerminal();
      // Render all commands in array
      // This happens when we just switch to Terminal from other tabs
      if (commands.length > 0) {
        for (let i = 0; i < commands.length; i += 1) {
          renderCommand(commands[i], terminal.current);
        }
        lastCommandIndex.current = commands.length;
      }
    }

    return () => {
      terminal.current?.dispose();
    };
  }, [commands]);

  React.useEffect(() => {
    // Render new commands when they are added to the commands array
    if (
      terminal.current &&
      commands.length > 0 &&
      lastCommandIndex.current < commands.length
    ) {
      for (let i = lastCommandIndex.current; i < commands.length; i += 1) {
        renderCommand(commands[i], terminal.current);
      }
      lastCommandIndex.current = commands.length;
    }
  }, [commands]);

  const clearTerminal = () => {
    terminal.current?.clear();
  };

  
  React.useEffect(() => {
    let resizeObserver: ResizeObserver | null = null;

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
      if (terminal.current) {
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
      } 
    resizeObserver = new ResizeObserver(() => {
      fitAddon.current?.fit();
    });

    if (ref.current) {
      resizeObserver.observe(ref.current);
    }

    return () => {
      resizeObserver?.disconnect();
    };
  }, []);

  return { ref, clearTerminal };
};
