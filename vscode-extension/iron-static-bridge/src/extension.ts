/**
 * IRON STATIC VS Code Bridge — extension entry point
 *
 * Starts an HTTP server on port 9880 (configurable).
 * Python scripts POST here to push notifications and events into VS Code.
 *
 * API:
 *   GET  /health              → 200 { ok: true, port }
 *   POST /notify              → VS Code notification (info / warn / error)
 *   POST /status              → status bar item update
 *   POST /progress            → progress notification
 *   POST /open                → open a file in the editor
 *   POST /event               → push a structured event into the LM tool queue
 */

import * as vscode from "vscode";
import { BridgeServer } from "./server";
import { peekEvents } from "./eventQueue";
import { registerChatParticipants } from "./chatParticipants";
import { registerLmTools } from "./lmTools";
import { registerHomeworkScheduler } from "./homeworkScheduler";
import { registerAudioRecorder } from "./audioRecorder";

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

  // Start the HTTP bridge server
  server = new BridgeServer(port, statusBarItem);
  server.start().catch((err: Error) => {
    vscode.window.showErrorMessage(
      `IRON STATIC Bridge failed to start on port ${port}: ${err.message}`
    );
    statusBarItem.text = "$(warning) IS Bridge offline";
  });

  // Chat participants — one per IRON STATIC agent persona
  registerChatParticipants(context);

  // Language model tools — automatically invoked by agent mode
  registerLmTools(context);

  // Homework scheduler — prerequisite reminders
  const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (workspaceRoot) {
    registerHomeworkScheduler(context, workspaceRoot);
    registerAudioRecorder(context, workspaceRoot);
  }

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand("ironStatic.showBridgeStatus", () => {
      const pending = peekEvents().length;
      vscode.window.showInformationMessage(
        `IRON STATIC Bridge is ${server?.running ? "running" : "stopped"} on port ${port}. ` +
        `${pending} event(s) queued for Arc.`
      );
    }),
    vscode.commands.registerCommand("ironStatic.stopBridge", () => {
      server?.stop();
      statusBarItem.text = "$(circle-slash) IS Bridge stopped";
      statusBarItem.backgroundColor = undefined;
    }),
    vscode.commands.registerCommand("ironStatic.startBridge", async () => {
      if (server?.running) {
        vscode.window.showInformationMessage("IRON STATIC Bridge is already running.");
        return;
      }
      server = new BridgeServer(port, statusBarItem);
      try {
        await server.start();
        statusBarItem.text = "$(radio-tower) IS :9880";
        statusBarItem.backgroundColor = undefined;
        statusBarItem.tooltip = `IRON STATIC Bridge — listening on port ${port}`;
        vscode.window.showInformationMessage(`IRON STATIC Bridge started on port ${port}.`);
      } catch (err) {
        vscode.window.showErrorMessage(
          `IRON STATIC Bridge failed to start on port ${port}: ${(err as Error).message}`
        );
        statusBarItem.text = "$(warning) IS Bridge offline";
      }
    })
  );

}


export function deactivate(): void {
  server?.stop();
}

