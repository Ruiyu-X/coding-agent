from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from agent.model_client import ChatModel
from agent.tools import LocalToolbox, ToolResult


SYSTEM_PROMPT = """You are a coding agent running in a local workspace.
You must complete programming tasks by planning, reading files, editing files,
running commands, and using observations to decide the next step.

Important rules:
- Reply with exactly one JSON object and no extra text.
- To use a tool, reply:
  {"thought": "...", "tool": "tool_name", "arguments": {...}}
- To finish, reply:
  {"thought": "...", "final": "brief completion summary"}
- Do not invent tool results. Use tools when you need file contents or command output.
- Start by understanding the workspace before editing.
- Prefer small, verifiable edits and run tests when possible.
- Use replace_in_file for focused edits when the original text is known.
- Do not use broad repeated replacements unless every occurrence has the same
  intended meaning. If unsure, rewrite the small file or replace a larger
  unique block instead.
- When adding tests, keep them inside the test class and update imports for new
  functions.
- If tests or commands fail, inspect the failing file and continue fixing until
  the tests pass or max_steps is reached.
- After adding tests, prefer discover_python_tests with expected_tests so you
  can verify the new tests were actually discovered, not merely that old tests
  still pass.
- Use diff_workspace before finalizing if you changed files.
"""


@dataclass
class AgentStep:
    thought: str
    action: str
    result: ToolResult | None


class CodingAgent:
    def __init__(
        self,
        model: ChatModel,
        toolbox: LocalToolbox,
        max_steps: int = 20,
        transcript_path: Path | None = None,
    ) -> None:
        self.model = model
        self.toolbox = toolbox
        self.max_steps = max_steps
        self.transcript_path = transcript_path
        self.steps: list[AgentStep] = []
        self.transcript: dict[str, Any] = {
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "workspace": str(toolbox.workspace),
            "max_steps": max_steps,
            "events": [],
        }

    def run(self, task: str) -> str:
        self.transcript["task"] = task
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n" + self.toolbox.describe()},
            {"role": "user", "content": f"Task: {task}"},
        ]

        try:
            for index in range(1, self.max_steps + 1):
                raw = self.model.complete(messages)
                decision = self._parse_json(raw)
                thought = str(decision.get("thought", ""))

                if "final" in decision:
                    final = str(decision["final"])
                    print(f"[step {index}] final: {final}")
                    self.steps.append(AgentStep(thought, "final", None))
                    self._record_event(index, decision, None)
                    self.transcript["final"] = final
                    return final

                tool_name = decision.get("tool")
                arguments = decision.get("arguments", {})
                if not isinstance(tool_name, str) or not isinstance(arguments, dict):
                    observation = (
                        "Invalid response. Expected a JSON object with string 'tool' "
                        "and object 'arguments', or a 'final' field."
                    )
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({"role": "user", "content": f"Observation: {observation}"})
                    self._record_event(
                        index,
                        {"thought": thought, "invalid_response": raw},
                        ToolResult(False, observation),
                    )
                    continue

                print(f"[step {index}] {thought}")
                print(f"[tool] {tool_name}({json.dumps(arguments, ensure_ascii=False)})")
                result = self.toolbox.run(tool_name, arguments)
                print(f"[observation] ok={result.ok}\n{result.output}\n")
                self.steps.append(AgentStep(thought, tool_name, result))
                self._record_event(index, decision, result)

                messages.append({"role": "assistant", "content": json.dumps(decision)})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Observation JSON: "
                            + json.dumps(
                                {"ok": result.ok, "output": result.output},
                                ensure_ascii=False,
                            )
                        ),
                    }
                )

            final = f"Stopped after reaching max_steps={self.max_steps}."
            self.transcript["final"] = final
            return final
        finally:
            self._save_transcript()

    def _record_event(
        self,
        step_index: int,
        decision: dict[str, Any],
        result: ToolResult | None,
    ) -> None:
        event: dict[str, Any] = {
            "step": step_index,
            "decision": decision,
        }
        if result is not None:
            event["observation"] = {"ok": result.ok, "output": result.output}
        self.transcript["events"].append(event)

    def _save_transcript(self) -> None:
        if self.transcript_path is None:
            return
        self.transcript["finished_at"] = datetime.now().isoformat(timespec="seconds")
        self.transcript_path.parent.mkdir(parents=True, exist_ok=True)
        self.transcript_path.write_text(
            json.dumps(self.transcript, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1))

        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and start < end:
            return json.loads(raw[start : end + 1])

        raise ValueError(f"Model did not return JSON: {raw}")
