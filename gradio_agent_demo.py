from __future__ import annotations

import argparse
import contextlib
import html
import io
import json
import os
import queue
import threading
import time
from pathlib import Path
from typing import Iterator

import gradio as gr

from agent.core import CodingAgent
from agent.model_client import MockModelClient, OpenAICompatibleClient
from agent.tools import LocalToolbox


LOCAL_NO_PROXY = "127.0.0.1,localhost,::1"

DEFAULT_TASK = (
    "Fix the calculator implementation, add safe divide, extend tests, "
    "and verify everything."
)

LOG_TAIL_LINES = 90

DEMO_CALCULATOR = """def add(a, b):
    return a - b


def subtract(a, b):
    return a + b
"""

DEMO_TESTS = """import unittest

from calculator import add, subtract


class CalculatorTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(2, 3), 5)

    def test_subtract(self):
        self.assertEqual(subtract(7, 4), 3)


if __name__ == "__main__":
    unittest.main()
"""

APP_CSS = """
:root {
    --agent-bg: #070b16;
    --agent-panel: rgba(15, 23, 42, 0.78);
    --agent-panel-soft: rgba(30, 41, 59, 0.78);
    --agent-line: rgba(148, 163, 184, 0.20);
    --agent-text: #e5edf7;
    --agent-muted: #9aa8bc;
    --agent-blue: #3b82f6;
    --agent-green: #22c55e;
    --agent-amber: #f59e0b;
    --agent-font: "Microsoft YaHei", "PingFang SC", "Segoe UI", Arial, sans-serif;
}

.gradio-container {
    background:
        linear-gradient(180deg, rgba(96, 165, 250, 0.18) 0%, rgba(96, 165, 250, 0.04) 18%, transparent 38%),
        radial-gradient(circle at 50% -18%, rgba(125, 211, 252, 0.34), transparent 34%),
        radial-gradient(circle at 9% 8%, rgba(59, 130, 246, 0.20), transparent 25%),
        radial-gradient(circle at 92% 10%, rgba(16, 185, 129, 0.14), transparent 26%),
        linear-gradient(135deg, #070b16 0%, #0f172a 46%, #111827 100%) !important;
    color: var(--agent-text) !important;
    font-family: var(--agent-font) !important;
}

.gradio-container * {
    letter-spacing: 0 !important;
}

.main-wrap {
    max-width: 1480px;
    margin: 0 auto;
}

.hero {
    position: relative;
    overflow: hidden;
    padding: 22px 26px;
    border: 1px solid var(--agent-line);
    border-radius: 8px;
    background:
        linear-gradient(90deg, rgba(125, 211, 252, 0.14), transparent 48%),
        linear-gradient(135deg, rgba(59, 130, 246, 0.20), rgba(17, 24, 39, 0.88));
    box-shadow: 0 24px 70px rgba(0, 0, 0, 0.32), inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.hero::before {
    content: "";
    position: absolute;
    top: -1px;
    left: 24px;
    right: 24px;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(191, 219, 254, 0.86), transparent);
}

.hero-title {
    margin: 0;
    font-size: 30px;
    line-height: 1.2;
    font-weight: 800;
}

.hero-subtitle {
    margin-top: 8px;
    color: var(--agent-muted);
    font-size: 15px;
}

.tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
}

.tag {
    padding: 5px 9px;
    border-radius: 6px;
    border: 1px solid rgba(96, 165, 250, 0.24);
    color: #bfdbfe;
    background: rgba(59, 130, 246, 0.12);
    font-size: 12px;
}

.dashboard-grid {
    display: grid;
    grid-template-columns: minmax(360px, 0.86fr) minmax(520px, 1.14fr);
    gap: 18px;
    align-items: stretch;
}

.file-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 18px;
    align-items: stretch;
}

.panel {
    box-sizing: border-box;
    height: 100%;
    border: 1px solid var(--agent-line) !important;
    border-radius: 8px !important;
    background:
        linear-gradient(180deg, rgba(30, 41, 59, 0.62), rgba(15, 23, 42, 0.86)),
        var(--agent-panel) !important;
    box-shadow: 0 18px 52px rgba(0, 0, 0, 0.24);
    padding: 16px !important;
}

.control-panel {
    display: flex !important;
    flex-direction: column !important;
}

.control-panel, .result-panel {
    min-height: 610px;
}

.file-panel {
    min-height: 720px;
}

.log-box {
    height: 470px;
    overflow: hidden;
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.42);
    padding: 12px 14px;
}

.log-box pre {
    height: 100%;
    margin: 0;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    color: #eff6ff;
    font: 13px/1.48 Consolas, "Cascadia Mono", "Microsoft YaHei", monospace;
}

.log-muted {
    color: var(--agent-muted);
}

.code-stack {
    display: grid;
    grid-template-rows: auto auto;
    gap: 16px;
}

.code-card {
    overflow: hidden;
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.42);
}

.code-title {
    display: inline-flex;
    margin: 8px 0 0 8px;
    padding: 5px 9px;
    border-radius: 6px;
    background: rgba(59, 130, 246, 0.82);
    color: #eff6ff;
    font-weight: 800;
    font-size: 12px;
}

.code-lines {
    margin: 10px 0 12px;
    font: 13px/1.55 Consolas, "Cascadia Mono", "Microsoft YaHei", monospace;
}

.code-row {
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr);
}

.line-no {
    color: #8aa0bd;
    text-align: right;
    padding-right: 12px;
    user-select: none;
}

.line-code {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    color: #dbeafe;
}

.transcript-code textarea,
.transcript-code .cm-editor,
.transcript-code .cm-scroller {
    min-height: 628px !important;
    max-height: 628px !important;
    overflow: auto !important;
}

.compact-output textarea {
    min-height: 76px !important;
}

.section-title {
    margin: 0 0 8px;
    font-size: 15px;
    font-weight: 760;
    color: #dbeafe;
}

textarea, input {
    border-radius: 8px !important;
}

button.primary {
    min-height: 44px !important;
    border-radius: 8px !important;
    font-weight: 800 !important;
}

.run-state {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 12px;
}

.state-tile {
    min-height: 70px;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid rgba(148, 163, 184, 0.18);
    background: rgba(15, 23, 42, 0.62);
}

.state-value {
    color: #eff6ff;
    font-size: 18px;
    font-weight: 850;
}

.state-label {
    margin-top: 4px;
    color: var(--agent-muted);
    font-size: 12px;
}

@media (max-width: 980px) {
    .dashboard-grid, .file-grid {
        grid-template-columns: 1fr;
    }
}
"""


def reset_demo_workspace(workspace: str) -> tuple[str, str]:
    root = Path(workspace).resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "calculator.py").write_text(DEMO_CALCULATOR, encoding="utf-8", newline="\n")
    (root / "test_calculator.py").write_text(DEMO_TESTS, encoding="utf-8", newline="\n")
    return code_html("calculator.py", DEMO_CALCULATOR), code_html("test_calculator.py", DEMO_TESTS)


def read_workspace_files(workspace: str) -> tuple[str, str]:
    root = Path(workspace).resolve()
    calculator = root / "calculator.py"
    tests = root / "test_calculator.py"
    return (
        calculator.read_text(encoding="utf-8") if calculator.exists() else "",
        tests.read_text(encoding="utf-8") if tests.exists() else "",
    )


def log_html(log: str) -> str:
    lines = log.splitlines()
    if len(lines) > LOG_TAIL_LINES:
        hidden = len(lines) - LOG_TAIL_LINES
        lines = [f"... showing latest {LOG_TAIL_LINES} lines, {hidden} earlier lines in transcript ..."] + lines[-LOG_TAIL_LINES:]
    escaped = html.escape("\n".join(lines) or "Waiting for agent output...")
    return f"<div class='log-box'><pre>{escaped}</pre></div>"


def code_html(title: str, code: str) -> str:
    rows = []
    for line_number, line in enumerate(code.splitlines() or [""], start=1):
        rows.append(
            "<div class='code-row'>"
            f"<span class='line-no'>{line_number}</span>"
            f"<span class='line-code'>{html.escape(line) or ' '}</span>"
            "</div>"
        )
    return (
        "<div class='code-card'>"
        f"<div class='code-title'>{html.escape(title)}</div>"
        f"<div class='code-lines'>{''.join(rows)}</div>"
        "</div>"
    )


class QueueWriter(io.StringIO):
    def __init__(self, updates: "queue.Queue[str]") -> None:
        super().__init__()
        self.updates = updates
        self.pending = ""

    def write(self, text: str) -> int:
        self.pending += text
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            self.updates.put(line + "\n")
        return len(text)

    def flush(self) -> None:
        if self.pending:
            self.updates.put(self.pending)
            self.pending = ""


def run_agent_stream(
    task: str,
    workspace: str,
    max_steps: int,
    use_mock: bool,
    save_transcript: bool,
) -> Iterator[tuple[str, str, str, str, str, str, str]]:
    transcript_path = Path(".agent_runs/gradio-last-run.json") if save_transcript else None
    updates: queue.Queue[str | tuple[str, str | None]] = queue.Queue()
    log = "Starting agent...\n"
    final_answer = ""
    calculator, tests = read_workspace_files(workspace)
    yield "Running", "0", final_answer, log_html(log), "", code_html("calculator.py", calculator), code_html("test_calculator.py", tests)

    def worker() -> None:
        try:
            model = MockModelClient() if use_mock else OpenAICompatibleClient.from_env()
            toolbox = LocalToolbox(Path(workspace).resolve())
            agent = CodingAgent(
                model=model,
                toolbox=toolbox,
                max_steps=int(max_steps),
                transcript_path=transcript_path,
            )
            writer = QueueWriter(updates)  # type: ignore[arg-type]
            with contextlib.redirect_stdout(writer):
                answer = agent.run(task)
            writer.flush()
            updates.put(("done", answer))
        except Exception as exc:
            updates.put(("error", f"{type(exc).__name__}: {exc}"))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    step_count = 0
    transcript = ""
    while True:
        try:
            item = updates.get(timeout=0.12)
        except queue.Empty:
            if thread.is_alive():
                continue
            break

        if isinstance(item, tuple):
            status, payload = item
            if status == "done":
                final_answer = payload or ""
                log += "\n=== Final Answer ===\n" + final_answer + "\n"
                break
            final_answer = payload or ""
            log += "\n[frontend error] " + final_answer + "\n"
            break

        log += item
        if item.startswith("[step "):
            step_count += 1
        if item.startswith("[observation]") or item.startswith("[step "):
            calculator, tests = read_workspace_files(workspace)
            yield "Running", str(step_count), final_answer, log_html(log), transcript, code_html("calculator.py", calculator), code_html("test_calculator.py", tests)
        time.sleep(0.05)

    if transcript_path and transcript_path.exists():
        data = json.loads(transcript_path.read_text(encoding="utf-8"))
        transcript = json.dumps(data, ensure_ascii=False, indent=2)

    calculator, tests = read_workspace_files(workspace)
    state = "Completed" if final_answer and not final_answer.startswith(("RuntimeError", "ValueError")) else "Stopped"
    yield state, str(step_count), final_answer, log_html(log), transcript, code_html("calculator.py", calculator), code_html("test_calculator.py", tests)


def build_demo(default_workspace: str) -> gr.Blocks:
    with gr.Blocks(
        title="Coding Agent Demo",
    ) as demo:
        gr.HTML(
            """
            <div class="main-wrap hero">
              <h1 class="hero-title">Coding Agent Runtime</h1>
              <div class="hero-subtitle">Self-managed loop for local code reading, editing, command execution, verification, and audit.</div>
              <div class="tag-row">
                <span class="tag">JSON tool actions</span>
                <span class="tag">Local file editing</span>
                <span class="tag">Command execution</span>
                <span class="tag">Syntax checks</span>
                <span class="tag">Test discovery</span>
                <span class="tag">Diff audit</span>
              </div>
            </div>
            """
        )

        with gr.Row(elem_classes=["main-wrap", "dashboard-grid"]):
            with gr.Column(scale=1, elem_classes=["panel", "control-panel"]):
                gr.HTML("<div class='section-title'>Task Control</div>")
                task = gr.Textbox(value=DEFAULT_TASK, lines=4, label="Programming task")
                workspace = gr.Textbox(value=default_workspace, label="Workspace")
                max_steps = gr.Slider(5, 40, value=30, step=1, label="Max steps")
                use_mock = gr.Checkbox(value=True, label="Use deterministic mock model")
                save_transcript = gr.Checkbox(value=True, label="Save JSON transcript")
                with gr.Row():
                    reset_btn = gr.Button("Reset demo workspace", variant="secondary")
                    run_btn = gr.Button("Run agent", variant="primary")

            with gr.Column(scale=1, elem_classes=["panel", "result-panel"]):
                gr.HTML("<div class='section-title'>Run Result</div>")
                with gr.Row():
                    run_state = gr.Textbox(value="Idle", label="State", interactive=False)
                    step_count = gr.Textbox(value="0", label="Observed steps", interactive=False)
                final_answer = gr.Textbox(label="Final answer", lines=3, elem_classes=["compact-output"])
                gr.HTML("<div class='section-title'>Agent log</div>")
                run_log = gr.HTML(value=log_html(""))

        with gr.Row(elem_classes=["main-wrap", "file-grid"]):
            with gr.Column(elem_classes=["panel", "file-panel"]):
                gr.HTML("<div class='section-title'>Workspace Files</div>")
                with gr.Column(elem_classes=["code-stack"]):
                    calculator_view = gr.HTML(value=code_html("calculator.py", ""))
                    tests_view = gr.HTML(value=code_html("test_calculator.py", ""))
            with gr.Column(elem_classes=["panel", "file-panel"]):
                gr.HTML("<div class='section-title'>Run Transcript</div>")
                transcript = gr.Code(language="json", label=".agent_runs/gradio-last-run.json", elem_classes=["transcript-code"])

        reset_btn.click(
            fn=reset_demo_workspace,
            inputs=[workspace],
            outputs=[calculator_view, tests_view],
        )
        run_btn.click(
            fn=run_agent_stream,
            inputs=[task, workspace, max_steps, use_mock, save_transcript],
            outputs=[run_state, step_count, final_answer, run_log, transcript, calculator_view, tests_view],
        )

    return demo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gradio frontend for the coding agent.")
    parser.add_argument("--workspace", default="demo_workspace")
    parser.add_argument("--server_name", default="127.0.0.1")
    parser.add_argument("--server_port", type=int, default=7860)
    parser.add_argument("--share", action="store_true")
    return parser.parse_args()


def main() -> None:
    os.environ["NO_PROXY"] = _merge_no_proxy(os.environ.get("NO_PROXY"))
    os.environ["no_proxy"] = _merge_no_proxy(os.environ.get("no_proxy"))
    args = parse_args()
    demo = build_demo(args.workspace)
    demo.queue().launch(
        server_name=args.server_name,
        server_port=args.server_port,
        share=args.share,
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="emerald",
            neutral_hue="slate",
        ),
        css=APP_CSS,
    )


def _merge_no_proxy(existing: str | None) -> str:
    entries = [entry.strip() for entry in (existing or "").split(",") if entry.strip()]
    for entry in LOCAL_NO_PROXY.split(","):
        if entry not in entries:
            entries.append(entry)
    return ",".join(entries)


if __name__ == "__main__":
    main()
