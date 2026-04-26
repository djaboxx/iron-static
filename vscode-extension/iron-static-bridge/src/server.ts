/**
 * BridgeServer — HTTP server that accepts POST requests from external tools
 * and translates them into VS Code API calls.
 *
 * Endpoints:
 *
 * GET  /health
 *   → 200 { ok: true, port: number, running: boolean }
 *
 * POST /notify
 *   body: { message: string, level?: "info"|"warn"|"error", actions?: string[] }
 *   → Shows a VS Code notification. If actions are provided and one is clicked,
 *     the response body echoes which action was chosen (fire-and-forget from
 *     the caller's perspective — they get 200 immediately).
 *
 * POST /status
 *   body: { text: string, tooltip?: string, color?: "green"|"yellow"|"red"|"blue"|string }
 *   → Updates the IRON STATIC status bar item.
 *
 * POST /progress
 *   body: { id: string, title: string, percent?: number, done?: boolean, message?: string }
 *   → Shows / updates / completes a progress notification.
 *     First call with an id creates it. Subsequent calls with same id update it.
 *     `done: true` dismisses it.
 *
 * POST /open
 *   body: { path: string, line?: number }
 *   → Opens the file in the editor, optionally jumping to a line.
 */

import http, { IncomingMessage, ServerResponse } from "http";
import * as vscode from "vscode";
import { pushEvent, peekEvents } from "./eventQueue";

type NotifyPayload = {
  message: string;
  level?: "info" | "warn" | "error";
  actions?: string[];
};

type StatusPayload = {
  text: string;
  tooltip?: string;
  color?: string;
};

type ProgressPayload = {
  id: string;
  title: string;
  percent?: number;
  done?: boolean;
  message?: string;
};

type OpenPayload = {
  path: string;
  line?: number;
};

type EventPayload = {
  source: string;
  type: "info" | "warn" | "error" | "done" | "progress";
  message: string;
  data?: Record<string, unknown>;
};

// Color name → VS Code ThemeColor id
const COLOR_MAP: Record<string, string> = {
  green: "statusBarItem.prominentBackground",
  yellow: "editorWarning.foreground",
  red: "statusBarItem.errorBackground",
  blue: "statusBarItem.remoteBackground",
};

// In-flight progress trackers: id → cancel token
const progressResolvers = new Map<string, () => void>();

function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve) => {
    let body = "";
    req.on("data", (chunk: Buffer) => (body += chunk.toString()));
    req.on("end", () => resolve(body));
  });
}

function json200(res: ServerResponse, data: object): void {
  res.writeHead(200, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

function err400(res: ServerResponse, msg: string): void {
  res.writeHead(400, { "Content-Type": "text/plain" });
  res.end(msg);
}

export class BridgeServer {
  private _server: http.Server;
  public running = false;

  constructor(
    private readonly port: number,
    private readonly statusBar: vscode.StatusBarItem
  ) {
    this._server = http.createServer(this._handle.bind(this));
  }

  start(): Promise<void> {
    return new Promise((resolve, reject) => {
      this._server.on("error", reject);
      this._server.listen(this.port, "127.0.0.1", () => {
        this.running = true;
        resolve();
      });
    });
  }

  stop(): void {
    this._server.close();
    this.running = false;
  }

  private async _handle(req: IncomingMessage, res: ServerResponse): Promise<void> {
    const url = req.url ?? "/";

    // Health check
    if (req.method === "GET" && url === "/health") {
      return json200(res, { ok: true, port: this.port, running: this.running, queued: peekEvents().length });
    }

    if (req.method !== "POST") {
      res.writeHead(405);
      return void res.end("Method not allowed");
    }

    let payload: Record<string, unknown>;
    try {
      payload = JSON.parse(await readBody(req));
    } catch {
      return err400(res, "Bad JSON");
    }

    // /notify → VS Code notification
    if (url === "/notify") {
      const { message, level = "info", actions = [] } = payload as NotifyPayload;
      if (!message) return err400(res, "message required");

      const show =
        level === "error"
          ? vscode.window.showErrorMessage
          : level === "warn"
          ? vscode.window.showWarningMessage
          : vscode.window.showInformationMessage;

      // Fire and forget — caller gets 200 immediately
      show(message, ...actions);
      return json200(res, { ok: true });
    }

    // /status → status bar update
    if (url === "/status") {
      const { text, tooltip, color } = payload as StatusPayload;
      if (!text) return err400(res, "text required");

      this.statusBar.text = `$(radio-tower) ${text}`;
      if (tooltip) this.statusBar.tooltip = tooltip;
      if (color) {
        const themeId = COLOR_MAP[color] ?? color;
        this.statusBar.backgroundColor = new vscode.ThemeColor(themeId);
      }
      return json200(res, { ok: true });
    }

    // /progress → progress notification
    if (url === "/progress") {
      const { id, title, percent, done, message } = payload as ProgressPayload;
      if (!id || !title) return err400(res, "id and title required");

      if (done) {
        // Resolve any in-flight progress for this id
        progressResolvers.get(id)?.();
        progressResolvers.delete(id);
        return json200(res, { ok: true, done: true });
      }

      if (!progressResolvers.has(id)) {
        // Create a new progress notification
        vscode.window.withProgress(
          {
            location: vscode.ProgressLocation.Notification,
            title,
            cancellable: false,
          },
          (progress) => {
            return new Promise<void>((resolve) => {
              progressResolvers.set(id, resolve);
              if (percent !== undefined) {
                progress.report({ increment: percent, message });
              } else if (message) {
                progress.report({ message });
              }
            });
          }
        );
      }
      return json200(res, { ok: true });
    }

    // /open → open file in editor
    if (url === "/open") {
      const { path: filePath, line } = payload as OpenPayload;
      if (!filePath) return err400(res, "path required");

      const uri = vscode.Uri.file(filePath);
      const doc = await vscode.workspace.openTextDocument(uri);
      const editor = await vscode.window.showTextDocument(doc);
      if (line !== undefined && line > 0) {
        const pos = new vscode.Position(line - 1, 0);
        editor.selection = new vscode.Selection(pos, pos);
        editor.revealRange(new vscode.Range(pos, pos));
      }
      return json200(res, { ok: true });
    }

    // /event → queue a structured event for the ironStatic_getEvents LM Tool
    if (url === "/event") {
      const { source, type, message, data } = payload as EventPayload;
      if (!source || !type || !message) return err400(res, "source, type, message required");

      pushEvent({ source, type, message, data });
      const pending = peekEvents().length;

      // Badge the status bar so Dave knows Arc has something to read
      this.statusBar.text = `$(radio-tower) IS :9880 $(bell) ${pending}`;
      this.statusBar.backgroundColor = new vscode.ThemeColor("statusBarItem.warningBackground");
      this.statusBar.tooltip = `${pending} IRON STATIC event(s) queued — ask Arc to check`;

      return json200(res, { ok: true, queued: pending });
    }

    res.writeHead(404);
    res.end("Not found");
  }
}
