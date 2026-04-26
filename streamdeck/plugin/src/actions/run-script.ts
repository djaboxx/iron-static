/**
 * run-script action
 *
 * Runs one of the IRON STATIC shell scripts silently (no terminal popup).
 * Configured per-button via the property inspector: { script: "01_session_start" }
 *
 * On key-down: exec the script, show alert on failure.
 * On appear:   title is set from the manifest default or left as-is.
 */

import streamDeck, {
  action,
  KeyDownEvent,
  SingletonAction,
  WillAppearEvent,
} from "@elgato/streamdeck";
import { execFile } from "child_process";
import path from "path";
import os from "os";

type Settings = {
  script: string; // e.g. "01_session_start"
};

// Resolve repo root relative to this plugin's install location.
// Plugin lives at: ~/Library/.../Plugins/com.iron-static.bridge.sdPlugin/bin/plugin.js
// Repo is at:      ~/git/iron-static
const REPO_ROOT = path.join(os.homedir(), "git", "iron-static");
const BUTTONS_DIR = path.join(REPO_ROOT, "streamdeck", "buttons");

@action({ UUID: "com.iron-static.bridge.run-script" })
export class RunScriptAction extends SingletonAction<Settings> {
  override async onKeyDown(ev: KeyDownEvent<Settings>): Promise<void> {
    const { script } = ev.payload.settings;
    if (!script) {
      await ev.action.showAlert();
      return;
    }

    const scriptPath = path.join(BUTTONS_DIR, `${script}.sh`);

    execFile(scriptPath, { timeout: 30_000 }, async (err: Error | null) => {
      if (err) {
        streamDeck.logger.error(`Script failed: ${scriptPath} — ${err.message}`);
        await ev.action.showAlert();
      }
    });
  }

  override async onWillAppear(_ev: WillAppearEvent<Settings>): Promise<void> {
    // No-op — title and icon come from the profile manifest
  }
}
