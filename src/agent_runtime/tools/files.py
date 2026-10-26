"""read_file and write_file. Both stay inside the workspace folder."""

from pathlib import Path
from typing import Any

from agent_runtime.tools.base import Tool

PATH_SCHEMA = {"path": {"type": "string", "description": "Path relative to the workspace."}}
MAX_READ_CHARS = 100_000


def _inside(root: Path, raw: str) -> Path:
    # resolve() follows ../ and symlinks, so a path that escapes the workspace is caught here.
    path = (root / raw).resolve()
    if not path.is_relative_to(root):
        raise ValueError("path is outside the workspace")
    # Dot files and folders can hold secrets (.env, .ssh, .aws): refuse any dotted part.
    if any(part.startswith(".") for part in path.relative_to(root).parts):
        raise ValueError("dot files and folders are blocked, they can hold secrets")
    return path


def make_read_file(root: Path) -> Tool:
    """Tool that reads a file inside root, up to 100,000 characters."""
    root = root.resolve()

    def run(args: dict[str, Any]) -> str:
        with _inside(root, str(args["path"])).open(encoding="utf-8") as f:
            return f.read(MAX_READ_CHARS)

    return Tool(
        name="read_file",
        description="Read a UTF-8 text file inside the workspace.",
        input_schema={"type": "object", "properties": PATH_SCHEMA, "required": ["path"]},
        run=run,
    )


def make_write_file(root: Path) -> Tool:
    """Tool that writes a file inside root. It overwrites the file."""
    root = root.resolve()

    def run(args: dict[str, Any]) -> str:
        path = _inside(root, str(args["path"]))
        path.write_text(str(args["content"]), encoding="utf-8")
        return f"wrote {len(str(args['content']))} chars"

    return Tool(
        name="write_file",
        description="Write a UTF-8 text file inside the workspace. Overwrites the file.",
        input_schema={
            "type": "object",
            "properties": {**PATH_SCHEMA, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
        run=run,
    )
