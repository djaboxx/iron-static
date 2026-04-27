/**
 * IRON STATIC Chat Participants
 *
 * Registers one VS Code chat participant per IRON STATIC agent persona.
 * Each participant loads its system prompt from the corresponding
 * .github/agents/<slug>.agent.md file and injects active song context
 * from database/songs.json before forwarding the request to a Copilot LLM.
 *
 * Usage in chat: @the-arranger what should the drop section look like?
 */

import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";

interface AgentDef {
  id: string;
  name: string;
  fullName: string;
  agentFile: string;
  icon: string;
  /** Optional preferred model family — overrides the default claude-sonnet selection */
  preferredModelFamily?: string;
}

const AGENTS: AgentDef[] = [
  {
    id: "iron-static.the-arranger",
    name: "the-arranger",
    fullName: "The Arranger",
    agentFile: ".github/agents/the-arranger.agent.md",
    icon: "list-ordered",
  },
  {
    id: "iron-static.the-critic",
    name: "the-critic",
    fullName: "The Critic",
    agentFile: ".github/agents/the-critic.agent.md",
    icon: "comment-discussion",
  },
  {
    id: "iron-static.the-sound-designer",
    name: "the-sound-designer",
    fullName: "The Sound Designer",
    agentFile: ".github/agents/the-sound-designer.agent.md",
    icon: "settings-gear",
  },
  {
    id: "iron-static.the-theorist",
    name: "the-theorist",
    fullName: "The Theorist",
    agentFile: ".github/agents/the-theorist.agent.md",
    icon: "book",
  },
  {
    id: "iron-static.the-live-engineer",
    name: "the-live-engineer",
    fullName: "The Live Engineer",
    agentFile: ".github/agents/the-live-engineer.agent.md",
    icon: "circuit-board",
  },
  {
    id: "iron-static.the-alchemist",
    name: "the-alchemist",
    fullName: "The Alchemist",
    agentFile: ".github/agents/the-alchemist.agent.md",
    icon: "beaker",
  },
  {
    id: "iron-static.the-mix-engineer",
    name: "the-mix-engineer",
    fullName: "The Mix Engineer",
    agentFile: ".github/agents/the-mix-engineer.agent.md",
    icon: "graph",
  },
  {
    id: "iron-static.the-visual-artist",
    name: "the-visual-artist",
    fullName: "The Visual Artist",
    agentFile: ".github/agents/the-visual-artist.agent.md",
    icon: "symbol-color",
  },
  {
    id: "iron-static.the-video-director",
    name: "the-video-director",
    fullName: "The Video Director",
    agentFile: ".github/agents/the-video-director.agent.md",
    icon: "play-circle",
  },
  {
    id: "iron-static.the-publicist",
    name: "the-publicist",
    fullName: "The Publicist",
    agentFile: ".github/agents/the-publicist.agent.md",
    icon: "megaphone",
  },
  {
    id: "iron-static.the-community-manager",
    name: "the-community-manager",
    fullName: "The Community Manager",
    agentFile: ".github/agents/the-community-manager.agent.md",
    icon: "globe",
  },
  {
    id: "iron-static.the-producer",
    name: "the-producer",
    fullName: "The Producer",
    agentFile: ".github/agents/the-producer.agent.md",
    icon: "organization",
  },
  {
    id: "iron-static.the-ace-step",
    name: "the-ace-step",
    fullName: "The ACE-Step",
    agentFile: ".github/agents/the-ace-step.agent.md",
    icon: "music",
  },
  {
    id: "iron-static.the-writer",
    name: "the-writer",
    fullName: "The Writer",
    agentFile: ".github/agents/the-writer.agent.md",
    icon: "edit",
    // GPT models are preferred for prose and lyric generation
    preferredModelFamily: "gpt-4.1",
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getWorkspaceRoot(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

function readFile(fullPath: string): string | undefined {
  try {
    return fs.readFileSync(fullPath, "utf-8");
  } catch {
    return undefined;
  }
}

/** Read active song context from database/songs.json */
function getActiveSongContext(workspaceRoot: string): string {
  const songsPath = path.join(workspaceRoot, "database", "songs.json");
  const raw = readFile(songsPath);
  if (!raw) {
    return "";
  }
  try {
    const songs: Array<{
      status: string;
      title: string;
      slug: string;
      key?: string;
      scale?: string;
      bpm?: number;
      time_signature?: string;
    }> = JSON.parse(raw);
    const active = songs.find((s) => s.status === "active");
    if (!active) {
      return "No active song currently set in database/songs.json.";
    }
    const parts = [
      `Active song: "${active.title}" (slug: ${active.slug})`,
      active.key && active.scale ? `Key: ${active.key} ${active.scale}` : null,
      active.bpm ? `BPM: ${active.bpm}` : null,
      active.time_signature ? `Time signature: ${active.time_signature}` : null,
    ].filter(Boolean);
    return parts.join(", ");
  } catch {
    return "";
  }
}

/** Load the agent's .agent.md system prompt, stripping YAML frontmatter */
function loadAgentSystemPrompt(agentFile: string, workspaceRoot: string): string {
  const fullPath = path.join(workspaceRoot, agentFile);
  const content = readFile(fullPath);
  if (!content) {
    return `You are an IRON STATIC music production agent. Help with the task.`;
  }
  // Strip YAML frontmatter (--- ... ---) — it's for VS Code, not for the LLM
  const stripped = content.replace(/^---[\s\S]*?---\n?/, "").trim();
  return stripped;
}

/** Build the prior conversation history for multi-turn context */
function buildHistory(
  history: readonly (vscode.ChatRequestTurn | vscode.ChatResponseTurn)[],
  agentFullName: string
): vscode.LanguageModelChatMessage[] {
  const messages: vscode.LanguageModelChatMessage[] = [];
  for (const turn of history) {
    if (turn instanceof vscode.ChatRequestTurn) {
      messages.push(vscode.LanguageModelChatMessage.User(turn.prompt));
    } else if (turn instanceof vscode.ChatResponseTurn) {
      const text = (turn as vscode.ChatResponseTurn).response
        .filter((p): p is vscode.ChatResponseMarkdownPart =>
          p instanceof vscode.ChatResponseMarkdownPart
        )
        .map((p) => p.value.value)
        .join("");
      if (text) {
        messages.push(vscode.LanguageModelChatMessage.Assistant(text));
      }
    }
  }
  return messages;
}

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

export function registerChatParticipants(context: vscode.ExtensionContext): void {
  for (const agent of AGENTS) {
    const handler: vscode.ChatRequestHandler = async (
      request,
      chatContext,
      stream,
      token
    ) => {
      const workspaceRoot = getWorkspaceRoot();
      if (!workspaceRoot) {
        stream.markdown(
          `**${agent.fullName}**: No workspace open — open the iron-static repo folder first.`
        );
        return;
      }

      const systemPrompt = loadAgentSystemPrompt(agent.agentFile, workspaceRoot);
      const songContext = getActiveSongContext(workspaceRoot);

      const systemBlock = [
        systemPrompt,
        "",
        "---",
        "## Current Session Context",
        songContext || "No active song.",
      ].join("\n");

      // Select model — Writer prefers GPT for prose; all others prefer Claude
      let models = agent.preferredModelFamily
        ? await vscode.lm.selectChatModels({
            vendor: "copilot",
            family: agent.preferredModelFamily,
          })
        : [];
      // Fallback chain: gpt-4o → claude-sonnet → any copilot model
      if (!models.length && agent.preferredModelFamily) {
        models = await vscode.lm.selectChatModels({
          vendor: "copilot",
          family: "gpt-4o",
        });
      }
      if (!models.length) {
        models = await vscode.lm.selectChatModels({
          vendor: "copilot",
          family: "claude-sonnet-4-5",
        });
      }
      if (!models.length) {
        models = await vscode.lm.selectChatModels({ vendor: "copilot" });
      }
      const model = models[0];
      if (!model) {
        stream.markdown(
          `**${agent.fullName}**: No language model available. Make sure GitHub Copilot is signed in.`
        );
        return;
      }

      // Build message list: system block as first user message, then history, then current request
      const messages: vscode.LanguageModelChatMessage[] = [
        vscode.LanguageModelChatMessage.User(systemBlock),
        ...buildHistory(
          chatContext.history.filter(
            (t): t is vscode.ChatRequestTurn => t instanceof vscode.ChatRequestTurn
          ),
          agent.fullName
        ),
        vscode.LanguageModelChatMessage.User(request.prompt),
      ];

      try {
        const response = await model.sendRequest(messages, {}, token);
        for await (const chunk of response.text) {
          stream.markdown(chunk);
        }
      } catch (err) {
        if (err instanceof vscode.LanguageModelError) {
          stream.markdown(`**${agent.fullName}** error: ${err.message} (${err.code})`);
          return;
        }
        throw err;
      }
    };

    const participant = vscode.chat.createChatParticipant(agent.id, handler);
    participant.iconPath = new vscode.ThemeIcon(agent.icon);
    context.subscriptions.push(participant);
  }
}
