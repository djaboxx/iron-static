#!/usr/bin/env python3
"""
rag_server.py — Local RAG query server for IRON STATIC.

Wraps ChromaDB + Ollama embeddings as a lightweight HTTP API on port 9882.
The VS Code extension calls POST /query to retrieve relevant knowledge chunks,
which are injected into chat participant system prompts.

Must run rag_index.py at least once before starting this server.

Usage:
    python scripts/rag_server.py
    python scripts/rag_server.py --port 9882
    python scripts/rag_server.py --model nomic-embed-text
    nohup python scripts/rag_server.py > /tmp/iron-static-rag.log 2>&1 &

Endpoints:
    GET  /health   → { "ok": true, "docs": N, "model": "..." }
    POST /query    → { "query": "...", "n_results": 5, "filter_type": null }
                   ← { "results": [{ "text", "source", "type", "title", "score" }] }
    POST /reload   → triggers rag_index.py in background, returns immediately

Requirements:
    chromadb>=0.5.0
    ollama>=0.3.0
"""

import argparse
import json
import logging
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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

EMBED_MODEL = "nomic-embed-text"
COLLECTION_NAME = "iron-static-knowledge"
DEFAULT_PORT = 9882


# ---------------------------------------------------------------------------
# RAG handler
# ---------------------------------------------------------------------------

class RagHandler:
    def __init__(
        self,
        persist_dir: Path,
        ollama_url: str,
        model: str,
        repo_root: Path,
    ) -> None:
        self.persist_dir = persist_dir
        self.ollama_url = ollama_url
        self.model = model
        self.repo_root = repo_root
        self._lock = threading.Lock()
        self._load_collection()

    def _load_collection(self) -> None:
        db_client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = db_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        log.info("Collection loaded: %d documents", self.collection.count())

    def health(self) -> dict:
        return {
            "ok": True,
            "docs": self.collection.count(),
            "model": self.model,
            "persist_dir": str(self.persist_dir),
        }

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        filter_type: Optional[str] = None,
    ) -> list[dict]:
        oc = ollama.Client(host=self.ollama_url)
        resp = oc.embed(model=self.model, input=[query_text])
        embedding: list[float] = resp.embeddings[0]  # type: ignore[index]

        total = self.collection.count()
        if total == 0:
            return []

        kwargs: dict = {
            "query_embeddings": [embedding],
            "n_results": min(n_results, total),
            "include": ["documents", "metadatas", "distances"],
        }
        if filter_type:
            kwargs["where"] = {"type": filter_type}

        results = self.collection.query(**kwargs)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        return [
            {
                "text": doc,
                "source": str(meta.get("source", "")),
                "type": str(meta.get("type", "")),
                "title": str(meta.get("title", "")),
                # cosine distance → similarity score (0–1, higher is better)
                "score": round(1.0 - float(dist), 4),
            }
            for doc, meta, dist in zip(docs, metas, distances)
        ]

    def reload(self) -> None:
        """Trigger rag_index.py in a background thread; reload collection when done."""
        def _run() -> None:
            script = self.repo_root / "scripts" / "rag_index.py"
            log.info("Re-indexing corpus via %s ...", script)
            try:
                subprocess.run([sys.executable, str(script)], check=True)
            except subprocess.CalledProcessError as exc:
                log.error("rag_index.py failed: %s", exc)
                return
            with self._lock:
                self._load_collection()
            log.info("Collection reloaded after re-index.")

        threading.Thread(target=_run, daemon=True).start()


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------

class RequestHandler(BaseHTTPRequestHandler):
    # Injected at class level before server starts
    rag: "RagHandler"

    def log_message(self, fmt: str, *args: object) -> None:  # type: ignore[override]
        log.debug("%s - %s", self.address_string(), fmt % args)

    def _send_json(self, data: object, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length > 0 else b""
        if not raw:
            return {}
        return json.loads(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(self.rag.health())
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/query":
            payload = self._read_body()
            query_text = str(payload.get("query", "")).strip()
            if not query_text:
                self._send_json({"error": "'query' field is required"}, 400)
                return
            n = int(payload.get("n_results", 5))
            filter_type: Optional[str] = payload.get("filter_type") or None
            try:
                results = self.rag.query(query_text, n, filter_type)
                self._send_json({"results": results})
            except Exception as exc:
                log.exception("Query error")
                self._send_json({"error": str(exc), "results": []}, 500)

        elif self.path == "/reload":
            self.rag.reload()
            self._send_json({"ok": True, "message": "Re-index started in background."})

        else:
            self._send_json({"error": "Not found"}, 404)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="IRON STATIC local RAG query server (ChromaDB + Ollama)"
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"HTTP port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--model", default=EMBED_MODEL,
        help=f"Ollama embedding model (default: {EMBED_MODEL})",
    )
    parser.add_argument(
        "--ollama-url", default="http://localhost:11434",
        help="Ollama base URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--persist-dir", default=None,
        help="ChromaDB persist directory (default: outputs/rag/chroma)",
    )
    parser.add_argument(
        "--repo-root", default=None,
        help="Repo root path (auto-detected from script location)",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else Path(__file__).parent.parent
    persist_dir = (
        Path(args.persist_dir)
        if args.persist_dir
        else repo_root / "outputs" / "rag" / "chroma"
    )
    persist_dir.mkdir(parents=True, exist_ok=True)

    rag = RagHandler(
        persist_dir=persist_dir,
        ollama_url=args.ollama_url,
        model=args.model,
        repo_root=repo_root,
    )
    RequestHandler.rag = rag

    server = ThreadingHTTPServer(("127.0.0.1", args.port), RequestHandler)
    log.info("RAG server listening on http://127.0.0.1:%d", args.port)
    log.info("  %d documents indexed", rag.collection.count())
    log.info("  embedding model: %s", args.model)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
