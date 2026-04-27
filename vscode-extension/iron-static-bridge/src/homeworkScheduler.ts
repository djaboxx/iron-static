/**
 * IRON STATIC Homework Scheduler
 *
 * Reads database/homework.json and reminds Dave of outstanding prerequisite
 * tasks that are blocking pipelines. Fires VS Code notifications on startup
 * and on a configurable interval.
 *
 * Commands:
 *   ironStatic.showHomework       — QuickPick of all open items; click to open JSON
 *   ironStatic.openHomework       — Open database/homework.json in editor
 *   ironStatic.markHomeworkDone   — Mark a homework item complete by ID
 */

import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface HomeworkItem {
  id: string;
  title: string;
  category: string;
  priority: "high" | "medium" | "low";
  done: boolean;
  notes: string;
  blocksWorkflow: string | null;
}

interface HomeworkFile {
  version: number;
  items: HomeworkItem[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getHomeworkPath(workspaceRoot: string): string {
  return path.join(workspaceRoot, "database", "homework.json");
}

function loadHomework(workspaceRoot: string): HomeworkFile | null {
  const p = getHomeworkPath(workspaceRoot);
  if (!fs.existsSync(p)) {
    return null;
  }
  try {
    return JSON.parse(fs.readFileSync(p, "utf-8")) as HomeworkFile;
  } catch {
    return null;
  }
}

function saveHomework(workspaceRoot: string, data: HomeworkFile): void {
  const p = getHomeworkPath(workspaceRoot);
  fs.writeFileSync(p, JSON.stringify(data, null, 2) + "\n", "utf-8");
}

function openItems(data: HomeworkFile): HomeworkItem[] {
  return data.items.filter((i) => !i.done);
}

function priorityIcon(p: HomeworkItem["priority"]): string {
  return p === "high" ? "🔴" : p === "medium" ? "🟡" : "🟢";
}

function categoryIcon(c: string): string {
  const icons: Record<string, string> = {
    platform: "🌐",
    secrets: "🔑",
    infrastructure: "🛠️",
    creative: "🎸",
  };
  return icons[c] ?? "📌";
}

// ---------------------------------------------------------------------------
// Status bar
// ---------------------------------------------------------------------------

let statusBarItem: vscode.StatusBarItem | undefined;

function updateStatusBar(pendingCount: number): void {
  if (!statusBarItem) {
    return;
  }
  if (pendingCount === 0) {
    statusBarItem.text = "$(check-all) Homework done";
    statusBarItem.tooltip = "All IRON STATIC prerequisites complete";
    statusBarItem.backgroundColor = undefined;
  } else {
    statusBarItem.text = `$(warning) ${pendingCount} homework`;
    statusBarItem.tooltip = `${pendingCount} IRON STATIC prerequisite task${pendingCount === 1 ? "" : "s"} outstanding — click to review`;
    const hasHighPriority =
      pendingCount > 0 &&
      !!(loadHomework(
        vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? ""
      )?.items.filter((i) => !i.done && i.priority === "high").length);
    statusBarItem.backgroundColor = hasHighPriority
      ? new vscode.ThemeColor("statusBarItem.warningBackground")
      : undefined;
  }
}

// ---------------------------------------------------------------------------
// Startup reminder
// ---------------------------------------------------------------------------

const LAST_REMINDER_KEY = "ironStatic.homework.lastReminderDate";

async function maybeShowStartupReminder(
  context: vscode.ExtensionContext,
  workspaceRoot: string
): Promise<void> {
  const cfg = vscode.workspace.getConfiguration("ironStatic.homework");
  if (!cfg.get<boolean>("showOnStartup", true)) {
    return;
  }

  const today = new Date().toISOString().split("T")[0];
  const lastDate = context.globalState.get<string>(LAST_REMINDER_KEY, "");
  if (lastDate === today) {
    return; // already shown today
  }

  const data = loadHomework(workspaceRoot);
  if (!data) {
    return;
  }
  const open = openItems(data);
  if (open.length === 0) {
    return;
  }

  await context.globalState.update(LAST_REMINDER_KEY, today);

  const highCount = open.filter((i) => i.priority === "high").length;
  const msg =
    `IRON STATIC: ${open.length} homework item${open.length === 1 ? "" : "s"} still open` +
    (highCount > 0 ? ` (${highCount} high-priority)` : "") +
    `. These are blocking pipelines.`;

  const action = await vscode.window.showWarningMessage(msg, "Review", "Dismiss");
  if (action === "Review") {
    vscode.commands.executeCommand("ironStatic.showHomework");
  }
}

// ---------------------------------------------------------------------------
// Interval reminder
// ---------------------------------------------------------------------------

let reminderInterval: ReturnType<typeof setInterval> | undefined;

function startReminderInterval(workspaceRoot: string): void {
  const cfg = vscode.workspace.getConfiguration("ironStatic.homework");
  const hours = cfg.get<number>("reminderIntervalHours", 0);
  if (hours <= 0) {
    return; // 0 = disabled
  }
  const ms = hours * 60 * 60 * 1000;
  reminderInterval = setInterval(() => {
    const data = loadHomework(workspaceRoot);
    if (!data) {
      return;
    }
    const open = openItems(data);
    if (open.length === 0) {
      return;
    }
    const high = open.filter((i) => i.priority === "high");
    const msg =
      high.length > 0
        ? `🔴 ${high.length} high-priority homework item${high.length === 1 ? "" : "s"} still blocking your IRON STATIC pipelines.`
        : `📋 ${open.length} homework item${open.length === 1 ? "" : "s"} still open for IRON STATIC.`;
    vscode.window
      .showInformationMessage(msg, "Review")
      .then((action) => {
        if (action === "Review") {
          vscode.commands.executeCommand("ironStatic.showHomework");
        }
      });
  }, ms);
}

function stopReminderInterval(): void {
  if (reminderInterval !== undefined) {
    clearInterval(reminderInterval);
    reminderInterval = undefined;
  }
}

// ---------------------------------------------------------------------------
// Public API used by lmTools.ts
// ---------------------------------------------------------------------------

export function getOpenHomework(workspaceRoot: string): HomeworkItem[] {
  const data = loadHomework(workspaceRoot);
  return data ? openItems(data) : [];
}

export function getAllHomework(workspaceRoot: string): HomeworkItem[] {
  const data = loadHomework(workspaceRoot);
  return data ? data.items : [];
}

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

export function registerHomeworkScheduler(
  context: vscode.ExtensionContext,
  workspaceRoot: string
): void {
  // Status bar item (left of bridge status)
  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    99
  );
  statusBarItem.command = "ironStatic.showHomework";
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // Initial render
  const initialData = loadHomework(workspaceRoot);
  updateStatusBar(initialData ? openItems(initialData).length : 0);

  // Watch for changes to homework.json
  const watcher = vscode.workspace.createFileSystemWatcher(
    new vscode.RelativePattern(workspaceRoot, "database/homework.json")
  );
  const refresh = () => {
    const d = loadHomework(workspaceRoot);
    updateStatusBar(d ? openItems(d).length : 0);
  };
  watcher.onDidChange(refresh);
  watcher.onDidCreate(refresh);
  context.subscriptions.push(watcher);

  // Commands
  context.subscriptions.push(
    // Show QuickPick of open items
    vscode.commands.registerCommand("ironStatic.showHomework", async () => {
      const data = loadHomework(workspaceRoot);
      if (!data) {
        vscode.window.showWarningMessage("No homework.json found in database/.");
        return;
      }
      const all = data.items;
      if (all.length === 0) {
        vscode.window.showInformationMessage("No homework items found.");
        return;
      }

      const picks = all.map((item) => ({
        label: `${item.done ? "$(check) " : "$(circle-slash) "}${priorityIcon(item.priority)} ${item.title}`,
        description: `${categoryIcon(item.category)} ${item.category}${item.blocksWorkflow ? ` · blocks ${item.blocksWorkflow}` : ""}`,
        detail: item.notes,
        id: item.id,
        done: item.done,
      }));

      const selected = await vscode.window.showQuickPick(picks, {
        placeHolder: `${openItems(data).length} of ${all.length} items outstanding — select to open homework.json`,
        matchOnDescription: true,
        matchOnDetail: true,
      });

      if (selected) {
        // Open homework.json at the selected item
        const docUri = vscode.Uri.file(getHomeworkPath(workspaceRoot));
        const doc = await vscode.workspace.openTextDocument(docUri);
        const editor = await vscode.window.showTextDocument(doc);
        // Jump to the line containing this item's ID
        const idLine = doc
          .getText()
          .split("\n")
          .findIndex((l) => l.includes(`"id": "${selected.id}"`));
        if (idLine >= 0) {
          const pos = new vscode.Position(idLine, 0);
          editor.selection = new vscode.Selection(pos, pos);
          editor.revealRange(
            new vscode.Range(pos, pos),
            vscode.TextEditorRevealType.InCenter
          );
        }
      }
    }),

    // Open homework.json
    vscode.commands.registerCommand("ironStatic.openHomework", () => {
      const docUri = vscode.Uri.file(getHomeworkPath(workspaceRoot));
      vscode.commands.executeCommand("vscode.open", docUri);
    }),

    // Mark an item done by ID (can be called from terminal or LM tools)
    vscode.commands.registerCommand(
      "ironStatic.markHomeworkDone",
      async (itemId?: string) => {
        const data = loadHomework(workspaceRoot);
        if (!data) {
          vscode.window.showErrorMessage("database/homework.json not found.");
          return;
        }

        let id = itemId;
        if (!id) {
          // Let user pick from open items
          const open = openItems(data);
          if (open.length === 0) {
            vscode.window.showInformationMessage("All homework items are already done. 🎉");
            return;
          }
          const pick = await vscode.window.showQuickPick(
            open.map((i) => ({
              label: `${priorityIcon(i.priority)} ${i.title}`,
              description: i.category,
              id: i.id,
            })),
            { placeHolder: "Mark which item as done?" }
          );
          if (!pick) {
            return;
          }
          id = pick.id;
        }

        const item = data.items.find((i) => i.id === id);
        if (!item) {
          vscode.window.showErrorMessage(`No homework item with id "${id}".`);
          return;
        }
        if (item.done) {
          vscode.window.showInformationMessage(`"${item.title}" is already marked done.`);
          return;
        }

        item.done = true;
        saveHomework(workspaceRoot, data);
        updateStatusBar(openItems(data).length);
        vscode.window.showInformationMessage(`✅ Marked done: "${item.title}"`);
      }
    )
  );

  // Startup reminder (once per day)
  maybeShowStartupReminder(context, workspaceRoot);

  // Interval reminder
  startReminderInterval(workspaceRoot);

  // Clean up interval on deactivation
  context.subscriptions.push({
    dispose: stopReminderInterval,
  });
}
