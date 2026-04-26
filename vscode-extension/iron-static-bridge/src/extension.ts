/**
 * IRON STATIC VS Code Bridge — extension entry point
 *
 * Starts an HTTP server on port 9880 (configurable).
 * Python scripts and the Stream Deck plugin POST here to push
 * notifications, status bar updates, and progress indicators
 * directly into the editor — without requiring VS Code to be
 * in the foreground.
 *
 * API:
 *   GET  /health              → 200 { ok: true, port }
 *   POST /notify              → VS Code notification (info / warn / error)
 *   POST /status              → status bar item update
 *   POST /progress            → progress notification (cancelable)
 *   POST /open                → open a file in the editor
 */

import * as vscode from "vscode";
import { BridgeServer } from "./server";

let server: BridgeServer | undefined;
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext): void {
  const port: number =
    vscode.workspace
      .getConfiguration("ironStatic.bridge")
      .get("port") ?? 9880;

  // Status bar indicator
  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100
  );
  statusBarItem.command = "ironStatic.showBridgeStatus";
  statusBarItem.text = "$(radio-tower) IS :9880";
  statusBarItem.tooltip = `IRON STATIC Bridge — listening on port ${port}`;
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // Start the server
  server = new BridgeServer(port, statusBarItem);
  server.start().catch((err: Error) => {
    vscode.window.showErrorMessage(
      `IRON STATIC Bridge failed to start on port ${port}: ${err.message}`
    );
    statusBarItem.text = "$(warning) IS Bridge offline";
  });

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand("ironStatic.showBridgeStatus", () => {
      vscode.window.showInformationMessage(
        `IRON STATIC Bridge is ${server?.running ? "running" : "stopped"} on port ${port}.`
      );
    }),
    vscode.commands.registerCommand("ironStatic.stopBridge", () => {
      server?.stop();
      statusBarItem.text = "$(circle-slash) IS Bridge stopped";
    })
  );
}

export function deactivate(): void {
  server?.stop();
}
