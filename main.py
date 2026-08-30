from __future__ import annotations

import argparse
from pathlib import Path

from agent.core import CodingAgent
from agent.model_client import MockModelClient, OpenAICompatibleClient
from agent.tools import LocalToolbox


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="A small coding agent with self-managed tool execution."
    )
    parser.add_argument("task", help="Programming task for the agent to complete.")
    parser.add_argument(
        "--workspace",
        default="demo_workspace",
        help="Directory the agent can inspect and modify.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=12,
        help="Maximum number of model/tool iterations.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use a deterministic mock model for demos and tests.",
    )
    parser.add_argument(
        "--transcript",
        default=".agent_runs/last-run.json",
        help="Path for the JSON run transcript. Use 'none' to disable.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workspace = Path(args.workspace).resolve()
    toolbox = LocalToolbox(workspace)
    model = MockModelClient() if args.mock else OpenAICompatibleClient.from_env()
    transcript_path = None if args.transcript.lower() == "none" else Path(args.transcript)
    agent = CodingAgent(
        model=model,
        toolbox=toolbox,
        max_steps=args.max_steps,
        transcript_path=transcript_path,
    )

    final_answer = agent.run(args.task)
    print("\n=== Final Answer ===")
    print(final_answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
