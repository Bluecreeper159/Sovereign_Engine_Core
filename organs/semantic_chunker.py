"""
organs/semantic_chunker.py
Sovereign Engine — Semantic Chunking Engine
Replaces raw [-4000:] file truncation with AST-aware, boundary-respecting chunking.
Exposes <index> and <read_chunk> primitives to the organism.
"""

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


MAX_CHUNK_TOKENS = 3000          # ~3k tokens per chunk ceiling
PREVIEW_LENGTH   = 120           # chars for index preview
TOKEN_ESTIMATE   = 4             # chars-per-token rough estimate


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    name: str                    # function name, class name, heading, etc.
    filepath: str
    start_line: int
    end_line: int
    content: str
    chunk_type: str              # 'function' | 'class' | 'heading' | 'block' | 'raw'

    @property
    def preview(self) -> str:
        return self.content[:PREVIEW_LENGTH].replace("\n", " ").strip()

    @property
    def estimated_tokens(self) -> int:
        return len(self.content) // TOKEN_ESTIMATE


@dataclass
class ChunkIndex:
    filepath: str
    file_type: str
    chunks: list[Chunk] = field(default_factory=list)

    def to_summary(self) -> str:
        """Compact index string injected into organism context via <index>."""
        lines = [f"[INDEX] {self.filepath} ({self.file_type}) — {len(self.chunks)} chunks\n"]
        for i, chunk in enumerate(self.chunks):
            lines.append(
                f"  [{i:02d}] {chunk.chunk_type:<10} | {chunk.name:<40} "
                f"L{chunk.start_line}-{chunk.end_line} | {chunk.preview!r}"
            )
        return "\n".join(lines)

    def get(self, name: str) -> Optional[Chunk]:
        """Retrieve chunk by exact name or case-insensitive partial match."""
        for chunk in self.chunks:
            if chunk.name == name:
                return chunk
        name_lower = name.lower()
        for chunk in self.chunks:
            if name_lower in chunk.name.lower():
                return chunk
        return None


# ---------------------------------------------------------------------------
# Internal chunkers per file type
# ---------------------------------------------------------------------------

def _chunk_python(source: str, filepath: str) -> list[Chunk]:
    """AST-aware chunking — never splits mid-function or mid-class."""
    chunks = []
    lines  = source.splitlines(keepends=True)

    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Fall back to raw chunking if the file won't parse
        return _chunk_raw(source, filepath)

    top_level = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and isinstance(getattr(node, 'col_offset', 0), int)
        and node.col_offset == 0          # top-level only
    ]
    top_level.sort(key=lambda n: n.lineno)

    # Module-level code before the first definition
    first_start = top_level[0].lineno if top_level else len(lines) + 1
    header_lines = lines[:first_start - 1]
    if header_lines:
        content = "".join(header_lines)
        chunks.append(Chunk(
            name="__module_header__",
            filepath=filepath,
            start_line=1,
            end_line=first_start - 1,
            content=content,
            chunk_type="block",
        ))

    for node in top_level:
        start = node.lineno
        end   = node.end_lineno or start
        content = "".join(lines[start - 1:end])
        chunk_type = (
            "class" if isinstance(node, ast.ClassDef) else "function"
        )
        chunks.append(Chunk(
            name=node.name,
            filepath=filepath,
            start_line=start,
            end_line=end,
            content=content,
            chunk_type=chunk_type,
        ))

    return chunks


def _chunk_markdown(source: str, filepath: str) -> list[Chunk]:
    """Chunk by H2 (##) headings minimum; H1 treated as a title block."""
    lines   = source.splitlines(keepends=True)
    chunks  = []
    pattern = re.compile(r'^#{1,3}\s+(.+)', re.MULTILINE)
    matches = list(pattern.finditer(source))

    if not matches:
        return _chunk_raw(source, filepath)

    boundaries = [(m.start(), m.group(1).strip()) for m in matches]
    # Map char offsets to line numbers
    char_to_line = {}
    pos = 0
    for i, line in enumerate(lines, 1):
        for _ in line:
            char_to_line[pos] = i
            pos += 1

    for idx, (char_start, heading) in enumerate(boundaries):
        char_end  = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(source)
        start_ln  = char_to_line.get(char_start, 1)
        end_ln    = char_to_line.get(char_end - 1, len(lines))
        content   = source[char_start:char_end]
        chunks.append(Chunk(
            name=heading,
            filepath=filepath,
            start_line=start_ln,
            end_line=end_ln,
            content=content,
            chunk_type="heading",
        ))

    return chunks


def _chunk_jsonl(source: str, filepath: str) -> list[Chunk]:
    """Each line is a self-contained JSON record; group into token-bounded chunks."""
    lines  = source.splitlines()
    chunks = []
    buffer = []
    buf_chars = 0
    start_ln  = 1

    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        buffer.append(line)
        buf_chars += len(line)
        if buf_chars >= MAX_CHUNK_TOKENS * TOKEN_ESTIMATE:
            chunks.append(Chunk(
                name=f"records_{start_ln}_{i}",
                filepath=filepath,
                start_line=start_ln,
                end_line=i,
                content="\n".join(buffer),
                chunk_type="block",
            ))
            buffer    = []
            buf_chars = 0
            start_ln  = i + 1

    if buffer:
        chunks.append(Chunk(
            name=f"records_{start_ln}_{len(lines)}",
            filepath=filepath,
            start_line=start_ln,
            end_line=len(lines),
            content="\n".join(buffer),
            chunk_type="block",
        ))

    return chunks


def _chunk_raw(source: str, filepath: str) -> list[Chunk]:
    """
    Fallback: split on blank lines (paragraph boundaries).
    Never splits mid-paragraph.
    """
    paragraphs = re.split(r'\n{2,}', source)
    chunks     = []
    current_ln = 1

    for idx, para in enumerate(paragraphs):
        if not para.strip():
            current_ln += para.count('\n') + 2
            continue
        line_count = para.count('\n') + 1
        chunks.append(Chunk(
            name=f"block_{idx:04d}",
            filepath=filepath,
            start_line=current_ln,
            end_line=current_ln + line_count - 1,
            content=para,
            chunk_type="raw",
        ))
        current_ln += line_count + 2   # account for the blank-line separator

    return chunks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class SemanticChunker:
    """
    Main organ. Wire into invoke_agent to replace raw file I/O.
    Usage:
        chunker = SemanticChunker()
        index   = chunker.index("/abs/path/to/file.py")
        print(index.to_summary())           # inject into <index> response
        chunk   = chunker.query("/abs/path/to/file.py", "function_name")
        print(chunk.content)                # inject into <read_chunk> response
    """

    def __init__(self, max_chunk_tokens: int = MAX_CHUNK_TOKENS):
        self.max_chunk_tokens = max_chunk_tokens
        self._cache: dict[str, ChunkIndex] = {}

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    def chunk(self, filepath: str) -> list[Chunk]:
        """Parse a file into semantic chunks. Cached per filepath."""
        path = Path(filepath).resolve()
        key  = str(path)

        if key in self._cache:
            return self._cache[key].chunks

        if not path.exists():
            raise FileNotFoundError(f"SemanticChunker: {filepath} not found")

        source = path.read_text(encoding="utf-8", errors="replace")
        suffix = path.suffix.lower()

        if suffix == ".py":
            chunks = _chunk_python(source, key)
        elif suffix in {".md", ".markdown"}:
            chunks = _chunk_markdown(source, key)
        elif suffix == ".jsonl":
            chunks = _chunk_jsonl(source, key)
        elif suffix == ".json":
            chunks = _chunk_raw(source, key)   # JSON is usually one blob
        else:
            chunks = _chunk_raw(source, key)

        # Merge tiny adjacent chunks to avoid context fragmentation
        chunks = self._merge_small(chunks)

        idx = ChunkIndex(filepath=key, file_type=suffix or "unknown", chunks=chunks)
        self._cache[key] = idx
        return chunks

    def index(self, filepath: str) -> ChunkIndex:
        """Return a ChunkIndex (builds cache if necessary)."""
        self.chunk(filepath)
        return self._cache[str(Path(filepath).resolve())]

    def query(self, filepath: str, query_hint: str) -> Optional[Chunk]:
        """
        Return the most relevant chunk for a query hint.
        Tries exact name match → partial match → first chunk.
        """
        idx = self.index(filepath)
        return idx.get(query_hint)

    def invalidate(self, filepath: str):
        """Call after a <mutate> write so stale chunks are evicted."""
        key = str(Path(filepath).resolve())
        self._cache.pop(key, None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _merge_small(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        Merge consecutive chunks that are individually below 200 tokens
        to avoid polluting the index with micro-chunks.
        """
        if not chunks:
            return chunks

        merged  = []
        current = chunks[0]

        for nxt in chunks[1:]:
            combined_tokens = current.estimated_tokens + nxt.estimated_tokens
            if combined_tokens <= 200:
                current = Chunk(
                    name=f"{current.name}+{nxt.name}",
                    filepath=current.filepath,
                    start_line=current.start_line,
                    end_line=nxt.end_line,
                    content=current.content + "\n" + nxt.content,
                    chunk_type=current.chunk_type,
                )
            else:
                merged.append(current)
                current = nxt

        merged.append(current)
        return merged


# ---------------------------------------------------------------------------
# XML primitive handlers — wire these into invoke_agent's tag dispatch
# ---------------------------------------------------------------------------

def handle_index(chunker: SemanticChunker, filepath: str) -> str:
    """
    Handler for <index path="/abs/path"> primitive.
    Returns a compact index summary string for context injection.
    """
    try:
        idx = chunker.index(filepath)
        return idx.to_summary()
    except FileNotFoundError as e:
        return f"[SemanticChunker ERROR] {e}"
    except Exception as e:
        return f"[SemanticChunker ERROR] Unexpected failure indexing {filepath}: {e}"


def handle_read_chunk(chunker: SemanticChunker, filepath: str, chunk_name: str) -> str:
    """
    Handler for <read_chunk path="/abs/path" chunk="name"> primitive.
    Returns the raw chunk content for context injection.
    """
    try:
        chunk = chunker.query(filepath, chunk_name)
        if chunk is None:
            idx = chunker.index(filepath)
            available = ", ".join(c.name for c in idx.chunks[:20])
            return (
                f"[SemanticChunker] Chunk '{chunk_name}' not found in {filepath}.\n"
                f"Available chunks: {available}"
            )
        header = (
            f"[CHUNK] {chunk.name} | {chunk.chunk_type} | "
            f"L{chunk.start_line}-{chunk.end_line} | ~{chunk.estimated_tokens} tokens\n"
            f"{'─' * 60}\n"
        )
        return header + chunk.content
    except FileNotFoundError as e:
        return f"[SemanticChunker ERROR] {e}"
    except Exception as e:
        return f"[SemanticChunker ERROR] Unexpected failure reading chunk: {e}"


# ---------------------------------------------------------------------------
# Standalone smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else __file__

    chunker = SemanticChunker()
    idx     = chunker.index(target)

    print(idx.to_summary())
    print()

    if idx.chunks:
        first = idx.chunks[0]
        print(f"\n--- First chunk preview: {first.name} ---")
        print(first.content[:400])
