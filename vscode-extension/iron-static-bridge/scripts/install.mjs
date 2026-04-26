/**
 * install.mjs — installs the extension into VS Code's extensions folder.
 *
 * Strategy: symlink the built extension dir into ~/.vscode/extensions/
 * so you can edit source, rebuild, and reload without re-copying.
 *
 * Usage: node scripts/install.mjs
 */
import { symlinkSync, existsSync, unlinkSync, mkdirSync } from "fs";
import { join } from "path";
import { homedir } from "os";
import { fileURLToPath } from "url";
import { execSync } from "child_process";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const EXT_DIR = join(homedir(), ".vscode", "extensions", "iron-static.iron-static-bridge-1.0.0");

// Remove stale symlink or dir
if (existsSync(EXT_DIR)) {
  unlinkSync(EXT_DIR);
}

// Symlink repo dir into extensions folder (dev-mode install)
symlinkSync(ROOT, EXT_DIR, "dir");
console.log(`Linked ${ROOT} → ${EXT_DIR}`);

// Prompt to reload
console.log("\nReload VS Code window to activate: Ctrl/Cmd+Shift+P → Reload Window");
