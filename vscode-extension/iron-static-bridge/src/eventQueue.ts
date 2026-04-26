/**
 * eventQueue.ts — shared in-memory event queue.
 *
 * Python scripts POST /event to the bridge server → events are pushed here.
 * The `ironStatic_getEvents` LM Tool drains and returns them to Copilot.
 */

export type BridgeEvent = {
  ts: string;           // ISO timestamp
  source: string;       // e.g. "run_brainstorm", "gcs_sync", "vela_vocalist"
  type: "info" | "warn" | "error" | "done" | "progress";
  message: string;
  data?: Record<string, unknown>; // optional structured payload
};

const queue: BridgeEvent[] = [];

export function pushEvent(event: Omit<BridgeEvent, "ts">): void {
  queue.push({ ts: new Date().toISOString(), ...event });
  // Cap queue at 100 events to prevent unbounded growth
  if (queue.length > 100) queue.shift();
}

/** Drain and return all queued events, then clear the queue. */
export function drainEvents(): BridgeEvent[] {
  return queue.splice(0);
}

/** Peek without clearing — for status checks. */
export function peekEvents(): BridgeEvent[] {
  return [...queue];
}
