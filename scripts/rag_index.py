#!/usr/bin/env python3
"""
rag_index.py — Index the IRON STATIC repo corpus into ChromaDB for local RAG.

Crawls docs/, knowledge/, database/, instruments/*/manuals/, .github/agents/,
and .github/skills/ for .md and .json files, chunks them, embeds via Ollama
(nomic-embed-text), and persists in outputs/rag/chroma/.

Only re-indexes files that have changed since the last run (content hash check).
Run with --force to re-index everything.

Usage:
    python scripts/rag_index.py
    python scripts/rag_index.py --force
    python scripts/rag_index.py --model nomic-embed-text:latest
    python scripts/rag_index.py --ollama-url http://localhost:11434

Requirements (add to scripts/requirements.txt):
    chromadb>=0.5.0
    ollama>=0.3.0
"""

import argparse
import hashlib
import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import chromadb
    import ollama
except ImportError:
    print(
        "ERROR: Missing dependencies. Run:\n"
        "  pip install chromadb ollama",
        file=sys.stderr,
    )
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 800        # characters per chunk
CHUNK_OVERLAP = 150     # character overlap between chunks
COLLECTION_NAME = "iron-static-knowledge"
EMBED_BATCH_SIZE = 32   # items per Ollama embed call

# (glob_pattern, doc_type) pairs — relative to repo root
INDEX_GLOBS = [
    ("docs/**/*.md", "doc"),
    ("knowledge/**/*.md", "knowledge"),
    ("database/*.json", "database"),
    ("instruments/*/manuals/**/*.md", "instrument-manual"),
    (".github/agents/*.agent.md", "agent"),
    (".github/skills/*/SKILL.md", "skill"),
    (".github/copilot-instructions.md", "doc"),
    (".github/instructions/*.md", "doc"),
]

# JSON files where each top-level item is a separate chunk (not the whole file)
ITEMIZED_JSON: set[str] = {
    "database/songs.json",
    "database/ableton_devices.json",
    "database/device_library.json",
    "database/instruments.json",
}


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character-level chunks."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def extract_title(content: str, filepath: str) -> str:
    """Extract the first # heading, or fall back to filename stem."""
    m = re.search(r"^#\s+(.+)", content, re.MULTILINE)
    return m.group(1).strip() if m else Path(filepath).stem


def file_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Indexer
# ---------------------------------------------------------------------------

class Indexer:
    def __init__(
        self,
        repo_root: Path,
        persist_dir: Path,
        ollama_url: str,
        model: str,
        force: bool,
    ) -> None:
        self.repo_root = repo_root
        self.persist_dir = persist_dir
        self.model = model
        self.force = force
        self.ollama_client = ollama.Client(host=ollama_url)
        db_client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = db_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._indexed = 0
        self._skipped = 0
        self._errors = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _embed(self, texts: list[str]) -> list[list[float]]:
        result = self.ollama_client.embed(model=self.model, input=texts)
        return result.embeddings  # type: ignore[return-value]

    def _already_indexed(self, doc_id: str, content_hash: str) -> bool:
        if self.force:
            return False
        try:
            existing = self.collection.get(ids=[doc_id], include=["metadatas"])
            if existing["ids"] and existing["metadatas"]:
                return existing["metadatas"][0].get("content_hash") == content_hash  # type: ignore[index]
        except Exception:
            pass
        return False

    def _upsert_chunks(
        self,
        chunks: list[str],
        source: str,
        doc_type: str,
        title: str,
        content_hash: str,
        id_prefix: Optional[str] = None,
    ) -> None:
        if not chunks:
            return
        prefix = id_prefix or source
        for batch_start in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[batch_start : batch_start + EMBED_BATCH_SIZE]
            embeddings = self._embed(batch)
            ids = [f"{prefix}::c{batch_start + i}" for i in range(len(batch))]
            metadatas = [
                {
                    "source": source,
                    "type": doc_type,
                    "title": title,
                    "chunk": batch_start + i,
                    "content_hash": content_hash,
                }
                for i in range(len(batch))
            ]
            self.collection.upsert(
                ids=ids, embeddings=embeddings, documents=batch, metadatas=metadatas
            )
        self._indexed += len(chunks)

    # ------------------------------------------------------------------
    # Per-file indexers
    # ------------------------------------------------------------------

    def index_markdown(self, filepath: Path, doc_type: str) -> None:
        rel = str(filepath.relative_to(self.repo_root))
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception as exc:
            log.warning("Cannot read %s: %s", rel, exc)
            self._errors += 1
            return
        if not content.strip():
            return
        h = file_hash(content)
        if self._already_indexed(rel, h):
            log.debug("  skip (unchanged): %s", rel)
            self._skipped += 1
            return
        title = extract_title(content, rel)
        chunks = chunk_text(content)
        log.info("  %s → %d chunks", rel, len(chunks))
        self._upsert_chunks(chunks, rel, doc_type, title, h)

    def index_json(self, filepath: Path, doc_type: str) -> None:
        rel = str(filepath.relative_to(self.repo_root))
        try:
            content = filepath.read_text(encoding="utf-8")
            data = json.loads(content)
        except Exception as exc:
            log.warning("Cannot read %s: %s", rel, exc)
            self._errors += 1
            return
        if not content.strip():
            return
        h = file_hash(content)
        if self._already_indexed(rel, h):
            log.debug("  skip (unchanged): %s", rel)
            self._skipped += 1
            return

        if rel in ITEMIZED_JSON:
            # Each top-level item → chunked text (large items are split further)
            items: list = data if isinstance(data, list) else list(data.values())
            chunks = []
            for item in items:
                chunks.extend(chunk_text(json.dumps(item, indent=2)))
            log.info("  %s → %d chunks (itemized)", rel, len(chunks))
            self._upsert_chunks(chunks, rel, doc_type, rel, h)
        else:
            # Treat the whole file as text and chunk it
            serialized = json.dumps(data, indent=2)
            chunks = chunk_text(serialized)
            log.info("  %s → %d chunks", rel, len(chunks))
            self._upsert_chunks(chunks, rel, doc_type, filepath.stem, h)

    # ------------------------------------------------------------------
    # Main runner
    # ------------------------------------------------------------------

    def run(self) -> None:
        log.info("Repo root   : %s", self.repo_root)
        log.info("Persist dir : %s", self.persist_dir)
        log.info("Model       : %s", self.model)
        log.info("Collection  : %s (%d existing docs)", COLLECTION_NAME, self.collection.count())

        for glob_pattern, doc_type in INDEX_GLOBS:
            files = sorted(self.repo_root.glob(glob_pattern))
            log.info("\n[%s] %s → %d files", doc_type, glob_pattern, len(files))
            for fp in files:
                if fp.suffix == ".json":
                    self.index_json(fp, doc_type)
                else:
                    self.index_markdown(fp, doc_type)

        log.info(
            "\nDone. Indexed: %d chunks  Skipped: %d files  Errors: %d  "
            "Total in collection: %d",
            self._indexed,
            self._skipped,
            self._errors,
            self.collection.count(),
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index the IRON STATIC repo into ChromaDB for local RAG."
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Path to iron-static repo root (auto-detected from script location)",
    )
    parser.add_argument(
        "--persist-dir",
        default=None,
        help="ChromaDB persist directory (default: outputs/rag/chroma)",
    )
    parser.add_argument(
        "--model",
        default=EMBED_MODEL,
        help=f"Ollama embedding model (default: {EMBED_MODEL})",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-index all files even if content hash is unchanged",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).parent.parent
    persist_dir = (
        Path(args.persist_dir) if args.persist_dir else repo_root / "outputs" / "rag" / "chroma"
    )
    persist_dir.mkdir(parents=True, exist_ok=True)

    Indexer(
        repo_root=repo_root,
        persist_dir=persist_dir,
        ollama_url=args.ollama_url,
        model=args.model,
        force=args.force,
    ).run()


if __name__ == "__main__":
    main()
