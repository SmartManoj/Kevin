import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import React from "react";
import { Command } from "#/state/commandSlice";
import { sendTerminalCommand } from "#/services/terminalService";

/*
  NOTE: Tests for this hook are indirectly covered by the tests for the XTermTerminal component.
  The reason for this is that the hook exposes a ref that requires a DOM element to be rendered.
*/

export const useTerminal = (commands: Command[] = []) => {
  const terminal = React.useRef<Terminal | null>(null);
  const fitAddon = React.useRef<FitAddon | null>(null);
  const ref = React.useRef<HTMLDivElement>(null);
  const lastCommandIndex = React.useRef(0);
  let lastCommand = React.useRef("");

  React.useEffect(() => {
    /* Create a new terminal instance */
    terminal.current = new Terminal({
      fontFamily: "Menlo, Monaco, 'Courier New', monospace",
      fontSize: 14,
      theme: {
        background: "#262626",
      },
    });
    fitAddon.current = new FitAddon();

    let resizeObserver: ResizeObserver;
    let commandBuffer = "";
    const terminalElement = terminal.current?.element;
    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault();
      navigator.clipboard.readText().then((text) => {
        terminal.current?.write(text);
        commandBuffer += text;
      });
    };

    if (ref.current) {
      /* Initialize the terminal in the DOM */
      terminal.current.loadAddon(fitAddon.current);
      terminal.current.open(ref.current);

      terminal.current.write("openhands@docker-desktop:/workspace $ ");
      terminal.current.onKey(({ key, domEvent }) => {
        if (domEvent.key === "Enter") {
          terminal.current?.write("\r\n");
          sendTerminalCommand(commandBuffer);
          lastCommand.current = commandBuffer;
          commandBuffer = "";
        } else if (domEvent.key === "Backspace") {
          if (commandBuffer.length > 0) {
            commandBuffer = commandBuffer.slice(0, -1);
            terminal.current?.write("\b \b");
          }
        } else {
          // Ignore paste event
          if (key.charCodeAt(0) === 22) {
            return;
          }
          commandBuffer += key;
          terminal.current?.write(key);
        }
      });
      terminal.current.attachCustomKeyEventHandler((arg) => {
        if (arg.ctrlKey && arg.code === "KeyV" && arg.type === "keydown") {
          navigator.clipboard.readText().then((text) => {
            terminal.current?.write(text);
            commandBuffer += text;
          });
        }
        if (arg.ctrlKey && arg.code === "KeyC" && arg.type === "keydown") {
          const selection = terminal.current?.getSelection();
          if (selection) {
            const clipboardItem = new ClipboardItem({
              "text/plain": new Blob([selection], { type: "text/plain" }),
            });

            navigator.clipboard.write([clipboardItem]);
          }
        }
        return true;
      });

      if (terminalElement) {
        // right click to paste
        terminalElement.addEventListener("contextmenu", handleContextMenu);
      }

      /* Listen for resize events */
      resizeObserver = new ResizeObserver(() => {
        fitAddon.current?.fit();
      });
      resizeObserver.observe(ref.current);
    }

    return () => {
      if (terminalElement) {
        terminalElement.removeEventListener("contextmenu", handleContextMenu);
      }
      terminal.current?.dispose();
      resizeObserver.disconnect();
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
        const command = commands[i];
        const lines = command.content.split("\n");

        lines.forEach((line, index) => {
          if (index < lines.length - 1 || command.type === "input") {
            terminal.current?.writeln(line);
          } else {
            terminal.current?.write(line);
          }
        });
      }

      lastCommandIndex.current = commands.length; // Update the position of the last command
    }
  }, [commands]);

  const clearTerminal = () => {
    terminal.current?.clear();
  };

  return { ref, clearTerminal };
};
