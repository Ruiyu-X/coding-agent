from __future__ import annotations

import json
import re
from dataclasses import dataclass

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
- Prefer small, verifiable edits and run tests when possible.
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
        max_steps: int = 12,
    ) -> None:
        self.model = model
        self.toolbox = toolbox
        self.max_steps = max_steps
        self.steps: list[AgentStep] = []

    def run(self, task: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n" + self.toolbox.describe()},
            {"role": "user", "content": f"Task: {task}"},
        ]

        for index in range(1, self.max_steps + 1):
            raw = self.model.complete(messages)
            decision = self._parse_json(raw)
            thought = str(decision.get("thought", ""))

            if "final" in decision:
                final = str(decision["final"])
                print(f"[step {index}] final: {final}")
                self.steps.append(AgentStep(thought, "final", None))
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
                continue

            print(f"[step {index}] {thought}")
            print(f"[tool] {tool_name}({json.dumps(arguments, ensure_ascii=False)})")
            result = self.toolbox.run(tool_name, arguments)
            print(f"[observation] ok={result.ok}\n{result.output}\n")
            self.steps.append(AgentStep(thought, tool_name, result))

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

        return f"Stopped after reaching max_steps={self.max_steps}."

    @staticmethod
    def _parse_json(raw: str) -> dict:
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
