/**
 * IRON STATIC VS Code Bridge — extension entry point
 *
 * Starts an HTTP server on port 9880 (configurable).
 * Python scripts POST here to push notifications and events into VS Code.
 *
 * Also registers an LM Tool — `ironStatic_getEvents` — so that Copilot
 * (Arc) can pull queued events directly without any user action required.
 *
 * Flow:
 *   Python script → POST /event → event queue (in memory)
 *   Arc           → calls ironStatic_getEvents tool → queue drains → Arc sees events
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
import { drainEvents, peekEvents } from "./eventQueue";

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
    })
  );

  // Register the LM Tool so Copilot (Arc) can pull queued events
  // Requires VS Code 1.93+ — guard so older versions don't crash
  if (typeof vscode.lm !== "undefined" && "registerTool" in vscode.lm) {
    const tool = (vscode.lm as typeof vscode.lm & {
      registerTool(name: string, impl: vscode.LanguageModelTool<void>): vscode.Disposable;
    }).registerTool("ironStatic_getEvents", {
      prepareInvocation(_options, _token) {
        const count = peekEvents().length;
        return {
          invocationMessage:
            count > 0
              ? `Draining ${count} IRON STATIC event(s) from bridge queue`
              : "No pending IRON STATIC events",
        };
      },
      invoke(_options, _token) {
        const events = drainEvents();
        // Update status bar to reflect cleared queue
        statusBarItem.text = "$(radio-tower) IS :9880";
        statusBarItem.backgroundColor = undefined;
        return new vscode.LanguageModelToolResult([
          new vscode.LanguageModelTextPart(
            events.length === 0
              ? "No events queued."
              : JSON.stringify(events, null, 2)
          ),
        ]);
      },
    });
    context.subscriptions.push(tool);
  }
}

export function deactivate(): void {
  server?.stop();
}

