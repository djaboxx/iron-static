/**
 * Status server — HTTP on port 9879
 *
 * Lets Python scripts push live data to Stream Deck button labels.
 * Used by manage_songs.py, bridge_client.py, run_repo_health.py, etc.
 *
 * Endpoints:
 *   GET  /health            → 200 {"ok": true}
 *   POST /status            body: {"action": "session-start", "title": "Session", "subtitle": "active"}
 *   POST /dial              body: {"label": "BPM", "value": "138"}
 *   POST /button            body: {"uuid": "com.iron-static.bridge.run-script", "title": "New title"}
 */

import http, { IncomingMessage, ServerResponse } from "http";
import type streamDeckType from "@elgato/streamdeck";
import { dialActions } from "./actions/dial-info.js";

const PORT = 9879;

type StatusPayload = {
  action?: string;
  title?: string;
  subtitle?: string;
};

type DialPayload = {
  label: string;
  value: string;
};

function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve) => {
    let body = "";
    req.on("data", (chunk: Buffer) => (body += chunk.toString()));
    req.on("end", () => resolve(body));
  });
}

export function startStatusServer(sd: typeof streamDeckType): void {
  const server = http.createServer(async (req: IncomingMessage, res: ServerResponse) => {
    const url = req.url ?? "/";

    // CORS for any local tool
    res.setHeader("Access-Control-Allow-Origin", "127.0.0.1");

    if (req.method === "GET" && url === "/health") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ok: true, port: PORT }));
      return;
    }

    if (req.method === "POST") {
      let payload: Record<string, string>;
      try {
        payload = JSON.parse(await readBody(req));
      } catch {
        res.writeHead(400);
        res.end("Bad JSON");
        return;
      }

      if (url === "/dial") {
        const { label, value } = payload as unknown as DialPayload;
        const dialAction = dialActions.get(label);
        if (dialAction) {
          await dialAction.setFeedback({ title: label, value });
        }
        res.writeHead(200);
        res.end("ok");
        return;
      }

      if (url === "/status") {
        const { title } = payload as StatusPayload;
        // Broadcast title update to all visible actions matching action name
        sd.actions.forEach(async (a) => {
          if (title) await a.setTitle(title);
        });
        res.writeHead(200);
        res.end("ok");
        return;
      }
    }

    res.writeHead(404);
    res.end("Not found");
  });

  server.on("error", (err: Error) => {
    sd.logger.error(`Status server error: ${err.message}`);
  });

  server.listen(PORT, "127.0.0.1", () => {
    sd.logger.info(`IRON STATIC status server listening on 127.0.0.1:${PORT}`);
  });
}
