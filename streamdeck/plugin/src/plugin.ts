/**
 * IRON STATIC Stream Deck Bridge Plugin
 *
 * Entry point — registers actions and starts the HTTP status receiver.
 * The status receiver lets Python scripts (bridge_client.py, manage_songs.py, etc.)
 * push live data to button labels on the deck.
 *
 * Port 9879 (HTTP):
 *   POST /status  { action: "session-start" | ... , title: "...", color?: "#rrggbb" }
 *   POST /bpm     { bpm: 138 }
 *   GET  /health  → 200 OK
 */

import streamDeck from "@elgato/streamdeck";
import { RunScriptAction } from "./actions/run-script.js";
import { DialInfoAction } from "./actions/dial-info.js";
import { startStatusServer } from "./status-server.js";

// Register actions before connecting
streamDeck.actions.registerAction(new RunScriptAction());
streamDeck.actions.registerAction(new DialInfoAction());

// Start HTTP receiver so Python scripts can push status to buttons
startStatusServer(streamDeck);

streamDeck.connect();
