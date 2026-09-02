from __future__ import annotations

import argparse
import contextlib
import io
import json
from pathlib import Path

import gradio as gr

from agent.core import CodingAgent
from agent.model_client import MockModelClient, OpenAICompatibleClient
from agent.tools import LocalToolbox


DEFAULT_TASK = (
    "Fix the calculator implementation, add safe divide, extend tests, "
    "and verify everything."
)

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
    --agent-bg: #0b1020;
    --agent-panel: #111827;
    --agent-panel-soft: #172033;
    --agent-line: rgba(148, 163, 184, 0.22);
    --agent-text: #e5edf7;
    --agent-muted: #9aa8bc;
    --agent-blue: #3b82f6;
    --agent-green: #22c55e;
    --agent-amber: #f59e0b;
    --agent-font: "Microsoft YaHei", "PingFang SC", "Segoe UI", Arial, sans-serif;
}

.gradio-container {
    background: linear-gradient(135deg, #0b1020 0%, #111827 56%, #152033 100%) !important;
    color: var(--agent-text) !important;
    font-family: var(--agent-font) !important;
}

.gradio-container * {
    letter-spacing: 0 !important;
}

.main-wrap {
    max-width: 1380px;
    margin: 0 auto;
}

.hero {
    padding: 20px 24px;
    border: 1px solid var(--agent-line);
    border-radius: 8px;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.16), rgba(17, 24, 39, 0.96));
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

.panel {
    border: 1px solid var(--agent-line) !important;
    border-radius: 8px !important;
    background: rgba(17, 24, 39, 0.94) !important;
    padding: 14px !important;
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
"""


def reset_demo_workspace(workspace: str) -> tuple[str, str, str]:
    root = Path(workspace).resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "calculator.py").write_text(DEMO_CALCULATOR, encoding="utf-8", newline="\n")
    (root / "test_calculator.py").write_text(DEMO_TESTS, encoding="utf-8", newline="\n")
    return (
        "Demo workspace reset to the initial buggy calculator project.",
        DEMO_CALCULATOR,
        DEMO_TESTS,
    )


def read_workspace_files(workspace: str) -> tuple[str, str]:
    root = Path(workspace).resolve()
    calculator = root / "calculator.py"
    tests = root / "test_calculator.py"
    return (
        calculator.read_text(encoding="utf-8") if calculator.exists() else "",
        tests.read_text(encoding="utf-8") if tests.exists() else "",
    )


def run_agent(
    task: str,
    workspace: str,
    max_steps: int,
    use_mock: bool,
    save_transcript: bool,
) -> tuple[str, str, str, str, str]:
    transcript_path = Path(".agent_runs/gradio-last-run.json") if save_transcript else None
    model = MockModelClient() if use_mock else OpenAICompatibleClient.from_env()
    toolbox = LocalToolbox(Path(workspace).resolve())
    agent = CodingAgent(
        model=model,
        toolbox=toolbox,
        max_steps=int(max_steps),
        transcript_path=transcript_path,
    )

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        final_answer = agent.run(task)

    transcript = ""
    if transcript_path and transcript_path.exists():
        data = json.loads(transcript_path.read_text(encoding="utf-8"))
        transcript = json.dumps(data, ensure_ascii=False, indent=2)

    calculator, tests = read_workspace_files(workspace)
    return final_answer, buffer.getvalue(), transcript, calculator, tests


def build_demo(default_workspace: str) -> gr.Blocks:
    with gr.Blocks(
        title="Coding Agent Demo",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="emerald",
            neutral_hue="slate",
        ),
        css=APP_CSS,
    ) as demo:
        gr.HTML(
            """
            <div class="main-wrap hero">
              <h1 class="hero-title">Coding Agent Runtime</h1>
              <div class="hero-subtitle">
                A self-managed programming agent that calls a language model,
                executes local tools, verifies tests, and records each run.
              </div>
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

        with gr.Row(elem_classes=["main-wrap"]):
            with gr.Column(scale=1, elem_classes=["panel"]):
                gr.HTML("<div class='section-title'>Task Control</div>")
                task = gr.Textbox(value=DEFAULT_TASK, lines=4, label="Programming task")
                workspace = gr.Textbox(value=default_workspace, label="Workspace")
                max_steps = gr.Slider(5, 40, value=30, step=1, label="Max steps")
                use_mock = gr.Checkbox(value=True, label="Use deterministic mock model")
                save_transcript = gr.Checkbox(value=True, label="Save JSON transcript")
                with gr.Row():
                    reset_btn = gr.Button("Reset demo workspace", variant="secondary")
                    run_btn = gr.Button("Run agent", variant="primary")
                reset_status = gr.Textbox(label="Workspace status", interactive=False)

            with gr.Column(scale=1, elem_classes=["panel"]):
                gr.HTML("<div class='section-title'>Run Result</div>")
                final_answer = gr.Textbox(label="Final answer", lines=3)
                run_log = gr.Textbox(label="Agent log", lines=20)

        with gr.Row(elem_classes=["main-wrap"]):
            with gr.Column(elem_classes=["panel"]):
                gr.HTML("<div class='section-title'>Workspace Files</div>")
                calculator_view = gr.Code(language="python", label="calculator.py")
                tests_view = gr.Code(language="python", label="test_calculator.py")
            with gr.Column(elem_classes=["panel"]):
                gr.HTML("<div class='section-title'>Run Transcript</div>")
                transcript = gr.Code(language="json", label=".agent_runs/gradio-last-run.json")

        reset_btn.click(
            fn=reset_demo_workspace,
            inputs=[workspace],
            outputs=[reset_status, calculator_view, tests_view],
        )
        run_btn.click(
            fn=run_agent,
            inputs=[task, workspace, max_steps, use_mock, save_transcript],
            outputs=[final_answer, run_log, transcript, calculator_view, tests_view],
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
    args = parse_args()
    demo = build_demo(args.workspace)
    demo.queue().launch(
        server_name=args.server_name,
        server_port=args.server_port,
        share=args.share,
    )


if __name__ == "__main__":
    main()
