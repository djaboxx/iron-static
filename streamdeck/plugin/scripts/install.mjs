/**
 * install.mjs — copies the built .sdPlugin to the Stream Deck Plugins folder.
 * Called by: npm run install-plugin
 */
import { cpSync, rmSync, existsSync } from "fs";
import { join } from "path";
import { homedir } from "os";

const src = new URL("../com.iron-static.bridge.sdPlugin", import.meta.url).pathname;
const dst = join(
  homedir(),
  "Library",
  "Application Support",
  "com.elgato.StreamDeck",
  "Plugins",
  "com.iron-static.bridge.sdPlugin"
);

if (existsSync(dst)) {
  rmSync(dst, { recursive: true, force: true });
}
cpSync(src, dst, { recursive: true });
console.log(`Installed → ${dst}`);
