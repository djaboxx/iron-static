/**
 * dial-info action (Encoder / touchscreen)
 *
 * Shows live info on the touchscreen strip above each dial.
 * Python scripts POST to port 9879 to push updated values here.
 *
 * Dial 0 → BPM display     (updated by manage_songs.py / bridge_client)
 * Dial 1 → Bridge status   (updated by bridge health check)
 * Dial 2 → Pigments M1     (updated by dial_bridge.py CC20 readback)
 * Dial 3 → Pigments M2     (updated by dial_bridge.py CC21 readback)
 *
 * Dial rotation is intentionally left to the MIDI plugin (already installed).
 */

import streamDeck, {
  action,
  DialAction,
  DialDownEvent,
  DialRotateEvent,
  SingletonAction,
  WillAppearEvent,
} from "@elgato/streamdeck";

type Settings = {
  label: string; // e.g. "BPM", "Bridge", "M1", "M2"
};

// In-memory store of visible dial action instances keyed by label.
// The status server uses this to push updates.
export const dialActions = new Map<string, DialAction<Settings>>();

@action({ UUID: "com.iron-static.bridge.dial-info" })
export class DialInfoAction extends SingletonAction<Settings> {
  override async onWillAppear(ev: WillAppearEvent<Settings>): Promise<void> {
    const { label } = ev.payload.settings;
    const dialAction = ev.action as DialAction<Settings>;
    if (label) {
      dialActions.set(label, dialAction);
    }
    await dialAction.setFeedback({ title: label ?? "—", value: "—" });
  }

  override async onDialRotate(ev: DialRotateEvent<Settings>): Promise<void> {
    const { label } = ev.payload.settings;
    streamDeck.logger.debug(`Dial rotate: ${label} ticks=${ev.payload.ticks}`);
  }

  override async onDialDown(ev: DialDownEvent<Settings>): Promise<void> {
    const { label } = ev.payload.settings;
    streamDeck.logger.debug(`Dial press: ${label}`);
  }
}
