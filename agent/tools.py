from __future__ import annotations

import difflib
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


MAX_OUTPUT_CHARS = 6000
MAX_SNAPSHOT_BYTES = 120_000


@dataclass
class ToolResult:
    ok: bool
    output: str


class LocalToolbox:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.initial_snapshot = self._snapshot_text_files()

    def run(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tools = {
            "workspace_summary": self.workspace_summary,
            "list_files": self.list_files,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "append_file": self.append_file,
            "replace_in_file": self.replace_in_file,
            "run_command": self.run_command,
            "discover_python_tests": self.discover_python_tests,
            "diff_workspace": self.diff_workspace,
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
            "- workspace_summary(): summarize file count, total bytes, and root path.\n"
            "- list_files(): recursively list files in the workspace.\n"
            "- read_file(path): read a UTF-8 text file.\n"
            "- write_file(path, content): create or replace a UTF-8 text file.\n"
            "- append_file(path, content): append text to a UTF-8 text file.\n"
            "- replace_in_file(path, old, new, expected_replacements=1): replace exact text.\n"
            "- run_command(command, timeout=30): run a shell command inside the workspace.\n"
            "- discover_python_tests(start_dir='.', pattern='test*.py', expected_tests=[]): "
            "run unittest discovery in verbose mode and verify expected test names appear.\n"
            "- diff_workspace(): show a unified diff against the initial workspace snapshot."
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

    def workspace_summary(self) -> ToolResult:
        file_count = 0
        total_bytes = 0
        for root, dirs, files in os.walk(self.workspace):
            dirs[:] = [directory for directory in dirs if not self._is_ignored_dir(directory)]
            for file_name in files:
                path = Path(root) / file_name
                file_count += 1
                total_bytes += path.stat().st_size
        summary = {
            "workspace": str(self.workspace),
            "file_count": file_count,
            "total_bytes": total_bytes,
            "captured_at": datetime.now().isoformat(timespec="seconds"),
        }
        return ToolResult(True, str(summary))

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

    def replace_in_file(
        self,
        path: str,
        old: str,
        new: str,
        expected_replacements: int = 1,
    ) -> ToolResult:
        target = self._resolve(path)
        content = target.read_text(encoding="utf-8")
        count = content.count(old)
        if count != expected_replacements:
            return ToolResult(
                False,
                (
                    f"Expected {expected_replacements} occurrence(s) in {path}, "
                    f"but found {count}. No changes were made."
                ),
            )
        updated = content.replace(old, new, expected_replacements)
        target.write_text(updated, encoding="utf-8", newline="\n")
        return ToolResult(True, f"Replaced {count} occurrence(s) in {path}.")

    def run_command(self, command: str, timeout: int = 30) -> ToolResult:
        command_to_run = self._normalize_python_command(command)
        completed = subprocess.run(
            command_to_run,
            cwd=self.workspace,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        output = (
            f"exit_code={completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
        return ToolResult(completed.returncode == 0, self._truncate(output))

    def discover_python_tests(
        self,
        start_dir: str = ".",
        pattern: str = "test*.py",
        expected_tests: list[str] | None = None,
        timeout: int = 30,
    ) -> ToolResult:
        start_path = self._resolve(start_dir)
        if not start_path.is_dir():
            return ToolResult(False, f"Test start directory does not exist: {start_dir}")

        command = (
            f'"{sys.executable}" -m unittest discover '
            f'-s "{start_path}" -p "{pattern}" -v'
        )
        completed = subprocess.run(
            command,
            cwd=self.workspace,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        combined = completed.stdout + "\n" + completed.stderr
        discovered = self._parse_unittest_names(combined)
        expected = expected_tests or []
        missing = [
            test_name
            for test_name in expected
            if not any(test_name in discovered_name for discovered_name in discovered)
        ]
        output = (
            f"exit_code={completed.returncode}\n"
            f"discovered_count={len(discovered)}\n"
            f"discovered_tests={discovered}\n"
            f"missing_expected_tests={missing}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
        return ToolResult(completed.returncode == 0 and not missing, self._truncate(output))

    def diff_workspace(self) -> ToolResult:
        current = self._snapshot_text_files()
        paths = sorted(set(self.initial_snapshot) | set(current))
        chunks: list[str] = []
        for path in paths:
            before = self.initial_snapshot.get(path, "")
            after = current.get(path, "")
            if before == after:
                continue
            chunks.extend(
                difflib.unified_diff(
                    before.splitlines(),
                    after.splitlines(),
                    fromfile=f"before/{path}",
                    tofile=f"after/{path}",
                    lineterm="",
                )
            )
        if not chunks:
            return ToolResult(True, "(no workspace changes)")
        return ToolResult(True, self._truncate("\n".join(chunks)))

    def _snapshot_text_files(self) -> dict[str, str]:
        snapshot: dict[str, str] = {}
        for root, dirs, files in os.walk(self.workspace):
            dirs[:] = [directory for directory in dirs if not self._is_ignored_dir(directory)]
            for file_name in files:
                path = Path(root) / file_name
                if path.stat().st_size > MAX_SNAPSHOT_BYTES:
                    continue
                rel_path = str(path.relative_to(self.workspace)).replace("\\", "/")
                try:
                    snapshot[rel_path] = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
        return snapshot

    @staticmethod
    def _is_ignored_dir(directory: str) -> bool:
        return directory in {".git", "__pycache__", ".pytest_cache", ".venv", "venv", ".agent_runs"}

    @staticmethod
    def _parse_unittest_names(output: str) -> list[str]:
        names: list[str] = []
        for line in output.splitlines():
            match = re.match(r"^(test[\w_]+)\s+\(([^)]+)\)\s+\.\.\.", line.strip())
            if match:
                names.append(match.group(2))
        return names

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
