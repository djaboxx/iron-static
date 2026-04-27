/**
 * velaPipeline.ts — Full post-recording pipeline for IRON STATIC
 *
 * Pipeline steps:
 *   1. Analyze audio (analyze_audio.py) — key, BPM, spectral character
 *   2. Transcribe (gemini_listen.py) — Gemini speech-to-text
 *   3. Forge music spec (gemini_forge.py) — Gemini generates a structured
 *      audio creation spec grounded in the transcription + active song context
 *   4. Generate images (generate_promo_image.py) — Imagen 3 cover art
 *
 * Optional steps (withMusicBed: true):
 *   5. Generate music bed (gemini_forge.py --acestep) — ACE-Step instrumental
 *   6. Mix vocal + music bed (ffmpeg amix) — blend at 100%/40% levels
 *
 *   7. Render waveform video (render_waveform_video.py) — uses mixed audio if available
 *
 * Each step is skipped (with a warning) rather than blocking if a prerequisite
 * is missing (e.g. no OPENAI_API_KEY, no GEMINI_API_KEY, no ffmpeg).
 *
 * Progress is streamed to VS Code's progress notification.
 * A summary panel shows all outputs when the pipeline completes.
 */

import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import { spawn } from "child_process";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface StepResult {
  step: string;
  skipped: boolean;
  skipReason?: string;
  stdout: string;
  stderr: string;
  exitCode: number;
  durationMs: number;
}

interface PipelineOptions {
  withMusicBed?: boolean;
}

interface PipelineResult {
  audioFile: string;
  steps: StepResult[];
  outputs: {
    analysis?: Record<string, unknown>;
    transcription?: string;
    forgeSpecPath?: string;
    musicBedPath?: string;
    mixedAudioPath?: string;
    critiqueText?: string;
    imagePaths?: string[];
    videoPaths?: string[];
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function findPython(workspaceRoot: string): string {
  const candidates = [
    path.join(workspaceRoot, ".venv", "bin", "python3"),
    "/Users/darnold/venv/bin/python3",
    "python3",
    "python",
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) { return c; }
  }
  return "python3"; // let PATH sort it out
}

function runScript(
  python: string,
  workspaceRoot: string,
  scriptArgs: string[],
  token: vscode.CancellationToken
): Promise<{ stdout: string; stderr: string; exitCode: number }> {
  return new Promise((resolve) => {
    const proc = spawn(python, scriptArgs, {
      cwd: workspaceRoot,
      env: { ...process.env },
    });

    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d: Buffer) => { stdout += d.toString(); });
    proc.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });

    const cancelSub = token.onCancellationRequested(() => {
      try { proc.kill("SIGTERM"); } catch { /* ignore */ }
    });

    proc.on("close", (code) => {
      cancelSub.dispose();
      resolve({ stdout, stderr, exitCode: code ?? 1 });
    });
  });
}

async function runStep(
  name: string,
  python: string,
  workspaceRoot: string,
  scriptArgs: string[],
  token: vscode.CancellationToken,
  skipIf?: () => string | null
): Promise<StepResult> {
  if (skipIf) {
    const reason = skipIf();
    if (reason) {
      return { step: name, skipped: true, skipReason: reason, stdout: "", stderr: "", exitCode: 0, durationMs: 0 };
    }
  }
  const t0 = Date.now();
  const { stdout, stderr, exitCode } = await runScript(python, workspaceRoot, scriptArgs, token);
  return { step: name, skipped: false, stdout, stderr, exitCode, durationMs: Date.now() - t0 };
}

// ---------------------------------------------------------------------------
// Pipeline runner
// ---------------------------------------------------------------------------

export async function runVelaPipeline(
  audioFile: string,
  workspaceRoot: string,
  options: PipelineOptions = {}
): Promise<void> {
  const { withMusicBed = false } = options;
  const python = findPython(workspaceRoot);
  const scripts = path.join(workspaceRoot, "scripts");
  const filename = path.basename(audioFile, ".wav");

  // Derive active song slug from songs.json
  let songSlug: string | null = null;
  try {
    const songs = JSON.parse(
      fs.readFileSync(path.join(workspaceRoot, "database", "songs.json"), "utf-8")
    );
    for (const s of (songs.songs ?? songs)) {
      if (s.status === "active") { songSlug = s.slug; break; }
    }
  } catch { /* non-fatal */ }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "IRON STATIC Pipeline",
      cancellable: true,
    },
    async (progress, token) => {
      const result: PipelineResult = { audioFile, steps: [], outputs: {} };
      const STEPS = withMusicBed ? 8 : 6; // +1 for critique in both variants
      let stepNum = 0;

      const report = (msg: string) => {
        stepNum++;
        progress.report({ message: `[${stepNum}/${STEPS}] ${msg}`, increment: 100 / STEPS });
      };

      // ── Step 1: Analyze audio ────────────────────────────────────────────
      report("Analyzing audio…");
      const analysisOutPath = path.join(workspaceRoot, "outputs", "audio_analysis", `${filename}_pipeline.json`);
      const step1 = await runStep(
        "analyze",
        python, workspaceRoot,
        [path.join(scripts, "analyze_audio.py"), audioFile, "--output", analysisOutPath],
        token
      );
      result.steps.push(step1);
      if (!step1.skipped && step1.exitCode === 0 && fs.existsSync(analysisOutPath)) {
        try { result.outputs.analysis = JSON.parse(fs.readFileSync(analysisOutPath, "utf-8")); } catch { /* ignore */ }
      }

      if (token.isCancellationRequested) { return showSummary(result); }

      // ── Step 2: Transcribe ───────────────────────────────────────────────
      report("Transcribing audio with Gemini…");
      const TRANSCRIBE_QUESTION =
        "Transcribe all speech or vocal content in this audio. Return only the transcribed text, nothing else. If there are no vocals or speech, return an empty string.";
      const step2 = await runStep(
        "transcribe",
        python, workspaceRoot,
        [
          path.join(scripts, "gemini_listen.py"),
          "--file", audioFile,
          "--question", TRANSCRIBE_QUESTION,
          "--output", "json",
        ],
        token,
        () => process.env.GEMINI_API_KEY ? null : "GEMINI_API_KEY not set — skipping transcription"
      );
      result.steps.push(step2);
      if (!step2.skipped && step2.exitCode === 0 && step2.stdout.trim()) {
        try {
          const parsed = JSON.parse(step2.stdout);
          result.outputs.transcription = parsed.analysis?.trim() || undefined;
        } catch { /* ignore */ }
      }

      if (token.isCancellationRequested) { return showSummary(result); }

      // ── Step 3: Forge music spec ─────────────────────────────────────────
      report("Forging music spec with Gemini…");
      const forgeTarget = result.outputs.transcription
        ? `vocal phrase: "${result.outputs.transcription.slice(0, 120)}"`
        : "vocal recording";
      const step3 = await runStep(
        "forge",
        python, workspaceRoot,
        [
          path.join(scripts, "gemini_forge.py"),
          "--target", forgeTarget,
          "--output", "json",
          ...(result.outputs.transcription
            ? ["--context", `Transcription: ${result.outputs.transcription.slice(0, 300)}`]
            : []),
        ],
        token,
        () => process.env.GEMINI_API_KEY ? null : "GEMINI_API_KEY not set — skipping spec generation"
      );
      result.steps.push(step3);
      if (!step3.skipped && step3.exitCode === 0 && step3.stdout.trim()) {
        try {
          const parsed = JSON.parse(step3.stdout);
          result.outputs.forgeSpecPath = parsed.spec_path;
        } catch { /* ignore */ }
      }

      if (token.isCancellationRequested) { return showSummary(result); }

      // ── Step 4: Generate images ──────────────────────────────────────────
      report("Generating cover images…");
      const step4 = await runStep(
        "images",
        python, workspaceRoot,
        [
          path.join(scripts, "generate_promo_image.py"),
          ...(songSlug ? ["--song", songSlug] : []),
          "--formats", "square", "landscape", "portrait",
        ],
        token,
        () => {
          if (!process.env.GEMINI_API_KEY) { return "GEMINI_API_KEY not set — skipping image generation"; }
          if (!songSlug) { return "No active song — skipping image generation"; }
          return null;
        }
      );
      result.steps.push(step4);
      if (!step4.skipped && step4.exitCode === 0 && songSlug) {
        const social = path.join(workspaceRoot, "outputs", "social");
        result.outputs.imagePaths = ["square", "landscape", "portrait"]
          .map((f) => path.join(social, `${songSlug}_cover_${f}.png`))
          .filter((p) => fs.existsSync(p));
      }

      if (token.isCancellationRequested) { return showSummary(result); }

      // ── Steps 5–6: Music bed + mix (optional) ───────────────────────────
      let audioForVideo = audioFile; // default: use the raw recording

      if (withMusicBed) {
        // ── Step 5: Generate music bed via ACE-Step ────────────────────────
        report("Generating music bed with ACE-Step…");
        const musicBedPath = path.join(
          workspaceRoot, "audio", "generated",
          `${songSlug ?? "iron-static"}_musicbed_${filename}.wav`
        );
        const acestepBase = process.env.ACESTEP_BASE ?? "http://127.0.0.1:8001";
        const step5 = await runStep(
          "music-bed",
          python, workspaceRoot,
          [
            path.join(scripts, "gemini_forge.py"),
            "--target", "instrumental music bed",
            "--acestep",
            "--acestep-url", acestepBase,
            "--acestep-duration", "60",
            "--no-gcs-push",
            "--output", "json",
            ...(result.outputs.transcription
              ? ["--context", `Vocal content: ${result.outputs.transcription.slice(0, 200)}`]
              : []),
          ],
          token,
          () => {
            try {
              const xhr = require("http").request;
              void xhr; // ACE-Step check is deferred to runtime
            } catch { /* ignore */ }
            return null; // always attempt — server check happens inside the script
          }
        );
        result.steps.push(step5);
        if (!step5.skipped && step5.exitCode === 0 && step5.stdout.trim()) {
          try {
            const parsed = JSON.parse(step5.stdout);
            const acestepPathStr: string | undefined = parsed.acestep_path;
            if (acestepPathStr && fs.existsSync(acestepPathStr)) {
              result.outputs.musicBedPath = acestepPathStr;
            }
          } catch { /* ignore */ }
        }

        if (token.isCancellationRequested) { return showSummary(result); }

        // ── Step 6: Mix vocal + music bed with ffmpeg ──────────────────────
        report("Mixing vocal + music bed…");
        const ffmpeg = fs.existsSync("/opt/homebrew/bin/ffmpeg")
          ? "/opt/homebrew/bin/ffmpeg"
          : "/usr/local/bin/ffmpeg";
        const mixedPath = path.join(
          workspaceRoot, "audio", "recordings",
          `${filename}_mixed.wav`
        );

        const step6 = await runStep(
          "mix",
          python, workspaceRoot, // python unused — we call ffmpeg directly
          [], token,
          () => {
            if (!result.outputs.musicBedPath) { return "No music bed generated — skipping mix"; }
            if (!fs.existsSync(ffmpeg)) { return "ffmpeg not found — skipping mix"; }
            return null;
          }
        );
        // Override: run ffmpeg directly for the mix step
        if (!step6.skipped) {
          const mixT0 = Date.now();
          const mixResult = await new Promise<{ exitCode: number; stderr: string }>((resolve) => {
            const args = [
              "-y",
              "-i", audioFile,
              "-i", result.outputs.musicBedPath!,
              "-filter_complex",
              "[0:a]volume=1.0[vocal];[1:a]volume=0.4[bed];[vocal][bed]amix=inputs=2:duration=first:dropout_transition=2[out]",
              "-map", "[out]",
              "-c:a", "pcm_s16le",
              mixedPath,
            ];
            const proc = spawn(ffmpeg, args, { cwd: workspaceRoot });
            let stderr = "";
            proc.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });
            token.onCancellationRequested(() => { try { proc.kill("SIGTERM"); } catch { /* ignore */ } });
            proc.on("close", (code) => resolve({ exitCode: code ?? 1, stderr }));
          });
          step6.exitCode = mixResult.exitCode;
          step6.stderr = mixResult.stderr;
          step6.durationMs = Date.now() - mixT0;
          if (mixResult.exitCode === 0 && fs.existsSync(mixedPath)) {
            result.outputs.mixedAudioPath = mixedPath;
            audioForVideo = mixedPath;
          }
        }
        result.steps.push(step6);

        if (token.isCancellationRequested) { return showSummary(result); }
      }

      // ── Critic step: qualitative critique of the mix ─────────────────────
      // Runs on the mixed audio if available, otherwise the raw recording.
      // Uses gemini_listen.py with the full IRON STATIC critique question.
      const CRITIC_QUESTION = [
        "Critique this audio as IRON STATIC's Critic. Cover:",
        "1. PERCEIVED KEY / MODE / SCALE — best guess even if uncertain.",
        "2. TEMPO — estimated BPM range, feel (rigid/loose/swung).",
        "3. DOMINANT TEXTURES — timbres, layers, spectral character.",
        "4. ENERGY & DYNAMICS — where does it hit, where does it breathe?",
        "5. IRON STATIC FIT — rate how well this fits our aesthetic (high/medium/low). Be honest.",
        "6. WHAT'S WORKING — specific elements that are strong.",
        "7. WHAT'S FIGHTING — specific elements that undermine the aesthetic.",
        "8. THREE CONCRETE SUGGESTIONS — actionable changes referencing specific instruments in our rig.",
      ].join(" ");

      const critiqueTarget = result.outputs.mixedAudioPath ?? audioFile;
      const critiqueLabel = result.outputs.mixedAudioPath ? "Critiquing mix…" : "Critiquing recording…";
      report(critiqueLabel);
      const stepCritique = await runStep(
        "critique",
        python, workspaceRoot,
        [
          path.join(scripts, "gemini_listen.py"),
          "--file", critiqueTarget,
          "--question", CRITIC_QUESTION,
          "--output", "json",
        ],
        token,
        () => process.env.GEMINI_API_KEY ? null : "GEMINI_API_KEY not set — skipping critique"
      );
      result.steps.push(stepCritique);
      if (!stepCritique.skipped && stepCritique.exitCode === 0 && stepCritique.stdout.trim()) {
        try {
          const parsed = JSON.parse(stepCritique.stdout);
          result.outputs.critiqueText = parsed.analysis?.trim() || undefined;
        } catch { /* ignore */ }
      }

      if (token.isCancellationRequested) { return showSummary(result); }

      // ── Step 5 or 7: Render video ────────────────────────────────────────
      report("Rendering waveform video…");
      const coverPath = songSlug
        ? path.join(workspaceRoot, "outputs", "social", `${songSlug}_cover_landscape.png`)
        : undefined;
      const stepVideo = await runStep(
        "video",
        python, workspaceRoot,
        [
          path.join(scripts, "render_waveform_video.py"),
          "--audio", audioForVideo,
          "--format", "landscape", "square",
          ...(coverPath && fs.existsSync(coverPath) ? ["--cover", coverPath] : []),
        ],
        token,
        () => {
          if (!fs.existsSync("/usr/local/bin/ffmpeg") && !fs.existsSync("/opt/homebrew/bin/ffmpeg")) {
            return "ffmpeg not found — skipping video render";
          }
          return null;
        }
      );
      result.steps.push(stepVideo);
      if (!stepVideo.skipped && stepVideo.exitCode === 0 && songSlug) {
        const social = path.join(workspaceRoot, "outputs", "social");
        result.outputs.videoPaths = ["landscape", "square"]
          .map((f) => path.join(social, `${songSlug}_waveform_${f}.mp4`))
          .filter((p) => fs.existsSync(p));
      }

      return showSummary(result);
    }
  );
}

// ---------------------------------------------------------------------------
// Summary panel
// ---------------------------------------------------------------------------

function showSummary(result: PipelineResult): void {
  const lines: string[] = [
    `# IRON STATIC Pipeline — ${path.basename(result.audioFile)}`,
    "",
  ];

  for (const s of result.steps) {
    const icon = s.skipped ? "⏭" : s.exitCode === 0 ? "✓" : "✗";
    const duration = s.durationMs > 0 ? ` (${(s.durationMs / 1000).toFixed(1)}s)` : "";
    lines.push(`## ${icon} ${s.step}${duration}`);
    if (s.skipped) {
      lines.push(`*Skipped: ${s.skipReason}*`);
    } else if (s.exitCode !== 0) {
      lines.push("**Failed.**");
      if (s.stderr.trim()) {
        lines.push("```");
        lines.push(s.stderr.trim().slice(-400));
        lines.push("```");
      }
    } else {
      lines.push("Completed.");
    }
    lines.push("");
  }

  if (result.outputs.transcription) {
    lines.push("## Transcription");
    lines.push(`> ${result.outputs.transcription}`);
    lines.push("");
    lines.push("*Run **Seed Brainstorm** in the recorder's post-save menu to use this as a creative seed.*");
    lines.push("");
  }

  if (result.outputs.analysis) {
    const a = result.outputs.analysis as Record<string, unknown>;
    lines.push("## Audio Analysis");
    if (a.key) { lines.push(`- **Key**: ${JSON.stringify(a.key)}`); }
    if (a.bpm) { lines.push(`- **BPM**: ${JSON.stringify(a.bpm)}`); }
    lines.push("");
  }

  if (result.outputs.imagePaths?.length) {
    lines.push("## Images Generated");
    for (const p of result.outputs.imagePaths) {
      lines.push(`- \`${path.basename(p)}\``);
    }
    lines.push("");
  }

  if (result.outputs.critiqueText) {
    lines.push("## The Critic");
    // Format each numbered line as its own paragraph for readability
    for (const line of result.outputs.critiqueText.split("\n")) {
      lines.push(line);
    }
    lines.push("");
  }

  if (result.outputs.musicBedPath) {
    lines.push("## Music Bed");
    lines.push(`Generated: \`${path.basename(result.outputs.musicBedPath)}\``);
    lines.push("");
  }

  if (result.outputs.mixedAudioPath) {
    lines.push("## Mixed Audio");
    lines.push(`Vocal + music bed: \`${path.basename(result.outputs.mixedAudioPath)}\``);
    lines.push("");
  }

  if (result.outputs.videoPaths?.length) {
    lines.push("## Videos Rendered");
    for (const p of result.outputs.videoPaths) {
      lines.push(`- \`${path.basename(p)}\``);
    }
    lines.push("");
  }

  if (result.outputs.forgeSpecPath) {
    lines.push("## Music Spec");
    lines.push(`Written to \`${result.outputs.forgeSpecPath}\``);
    lines.push("");
  }

  // Show as a virtual document
  const content = lines.join("\n");
  const uri = vscode.Uri.parse(
    `untitled:IRON_STATIC_Pipeline_${Date.now()}.md`
  );
  vscode.workspace.openTextDocument(uri).then((doc) => {
    vscode.window.showTextDocument(doc, { preview: true, viewColumn: vscode.ViewColumn.Beside }).then((editor) => {
      editor.edit((e) => {
        e.insert(new vscode.Position(0, 0), content);
      });
      // If a transcription was captured, offer to seed a brainstorm
      if (result.outputs.transcription) {
        vscode.window.showInformationMessage(
          "Transcription captured. Seed a brainstorm from it?",
          "Seed Brainstorm"
        ).then((action) => {
          if (action === "Seed Brainstorm") {
            seedBrainstormFromTranscription(result.outputs.transcription!, result.audioFile.replace(/\/[^/]+$/, ""));
          }
        });
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Seed brainstorm from transcription

/**
 * Run run_brainstorm.py --seed "<text>" --force to generate a new brainstorm
 * seeded from a vocal recording transcription.
 *
 * Shows progress while running and opens the result in a notification.
 */
export async function seedBrainstormFromTranscription(
  transcription: string,
  workspaceRoot: string
): Promise<void> {
  const python = await findPython(workspaceRoot);
  const scriptPath = path.join(workspaceRoot, "scripts", "run_brainstorm.py");

  if (!fs.existsSync(scriptPath)) {
    vscode.window.showErrorMessage(`run_brainstorm.py not found at ${scriptPath}`);
    return;
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "IRON STATIC — Seeding brainstorm from transcription…",
      cancellable: false,
    },
    async (progress) => {
      progress.report({ message: "Calling Gemini…" });

      const result = await new Promise<{ code: number; stdout: string; stderr: string }>(
        (resolve) => {
          let stdout = "";
          let stderr = "";
          const proc = spawn(python, [
            scriptPath,
            "--seed", transcription,
            "--force",
          ], { cwd: workspaceRoot });
          proc.stdout.on("data", (d: Buffer) => { stdout += d.toString(); });
          proc.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });
          proc.on("close", (code) => resolve({ code: code ?? 1, stdout, stderr }));
        }
      );

      if (result.code === 0) {
        // Extract the written path from the INFO log line
        const match = result.stderr.match(/Wrote (.+brainstorms\/.+\.md)/);
        const brainstormPath = match ? path.join(workspaceRoot, match[1]) : undefined;
        const msg = brainstormPath
          ? `Brainstorm seeded → ${path.basename(brainstormPath)}`
          : "Brainstorm seeded.";
        vscode.window.showInformationMessage(msg);
      } else {
        vscode.window.showErrorMessage(
          `Brainstorm seed failed (exit ${result.code}): ${result.stderr.slice(-300)}`
        );
      }
    }
  );
}
