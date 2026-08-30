from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


class ChatModel(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str:
        """Return the assistant's next message."""


@dataclass
class OpenAICompatibleClient:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.0
    timeout: int = 60

    @classmethod
    def from_env(cls) -> "OpenAICompatibleClient":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Set it or run with --mock for a local demo."
            )
        return cls(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0")),
        )

    def complete(self, messages: list[dict[str, str]]) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Model request failed: HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Model request failed: {exc}") from exc

        parsed = json.loads(raw)
        return parsed["choices"][0]["message"]["content"]


class MockModelClient:
    """A deterministic model double used for tests and screen-recorded demos."""

    def __init__(self) -> None:
        self.step = 0

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.step += 1
        if self.step == 1:
            return json.dumps(
                {
                    "thought": "Inspect the workspace before editing.",
                    "tool": "list_files",
                    "arguments": {},
                }
            )
        if self.step == 2:
            return json.dumps(
                {
                    "thought": "Read the calculator implementation.",
                    "tool": "read_file",
                    "arguments": {"path": "calculator.py"},
                }
            )
        if self.step == 3:
            return json.dumps(
                {
                    "thought": "Fix the arithmetic functions and keep the API stable.",
                    "tool": "write_file",
                    "arguments": {
                        "path": "calculator.py",
                        "content": (
                            "def add(a, b):\n"
                            "    return a + b\n\n\n"
                            "def subtract(a, b):\n"
                            "    return a - b\n"
                        ),
                    },
                }
            )
        if self.step == 4:
            return json.dumps(
                {
                    "thought": "Run the project tests to verify the change.",
                    "tool": "run_command",
                    "arguments": {"command": "python -m unittest discover -s ."},
                }
            )
        return json.dumps(
            {
                "thought": "The tests pass, so the task is complete.",
                "final": "Fixed calculator.py and verified it with unittest.",
            }
        )
