from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_OUTPUT_CHARS = 6000


@dataclass
class ToolResult:
    ok: bool
    output: str


class LocalToolbox:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def run(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tools = {
            "list_files": self.list_files,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "append_file": self.append_file,
            "run_command": self.run_command,
        }
        if name not in tools:
            return ToolResult(False, f"Unknown tool: {name}")
        try:
            return tools[name](**arguments)
        except TypeError as exc:
            return ToolResult(False, f"Invalid arguments for {name}: {exc}")
        except Exception as exc:
            return ToolResult(False, f"{type(exc).__name__}: {exc}")

    def describe(self) -> str:
        return (
            "Available tools:\n"
            "- list_files(): recursively list files in the workspace.\n"
            "- read_file(path): read a UTF-8 text file.\n"
            "- write_file(path, content): create or replace a UTF-8 text file.\n"
            "- append_file(path, content): append text to a UTF-8 text file.\n"
            "- run_command(command): run a shell command inside the workspace."
        )

    def _resolve(self, path: str) -> Path:
        candidate = (self.workspace / path).resolve()
        if candidate != self.workspace and self.workspace not in candidate.parents:
            raise ValueError(f"Path escapes workspace: {path}")
        return candidate

    def list_files(self) -> ToolResult:
        lines: list[str] = []
        ignored_dirs = {".git", "__pycache__", ".pytest_cache", ".venv", "venv"}
        for root, dirs, files in os.walk(self.workspace):
            dirs[:] = [directory for directory in dirs if directory not in ignored_dirs]
            rel_root = Path(root).relative_to(self.workspace)
            for file_name in sorted(files):
                rel_path = rel_root / file_name if str(rel_root) != "." else Path(file_name)
                lines.append(str(rel_path).replace("\\", "/"))
        return ToolResult(True, "\n".join(lines) if lines else "(workspace is empty)")

    def read_file(self, path: str) -> ToolResult:
        target = self._resolve(path)
        return ToolResult(True, self._truncate(target.read_text(encoding="utf-8")))

    def write_file(self, path: str, content: str) -> ToolResult:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        return ToolResult(True, f"Wrote {path} ({len(content)} chars).")

    def append_file(self, path: str, content: str) -> ToolResult:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8", newline="\n") as file:
            file.write(content)
        return ToolResult(True, f"Appended {len(content)} chars to {path}.")

    def run_command(self, command: str) -> ToolResult:
        command_to_run = self._normalize_python_command(command)
        completed = subprocess.run(
            command_to_run,
            cwd=self.workspace,
            shell=True,
            text=True,
            capture_output=True,
            timeout=30,
        )
        output = (
            f"exit_code={completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
        return ToolResult(completed.returncode == 0, self._truncate(output))

    @staticmethod
    def _normalize_python_command(command: str) -> str:
        stripped = command.strip()
        if stripped == "python":
            return f'"{sys.executable}"'
        if stripped.startswith("python "):
            return f'"{sys.executable}" {stripped[len("python ") :]}'
        return command

    @staticmethod
    def _truncate(text: str) -> str:
        if len(text) <= MAX_OUTPUT_CHARS:
            return text
        return text[:MAX_OUTPUT_CHARS] + "\n...<truncated>"
