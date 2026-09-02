# Video Script

Keep the recording under two minutes.

## Suggested Flow

1. Show the repository structure briefly.
2. Say that the project implements a small coding agent runtime, not a trained
   model and not a wrapper around an existing agent product.
3. Open `agent/core.py` and point out the loop: model decision, tool execution,
   observation, next step.
4. Open `agent/tools.py` and point out local tools such as file reading, writing,
   command execution, syntax checks, test discovery, and diff review.
5. Run the deterministic demo:

   ```bash
   python main.py "Fix the calculator implementation, add safe divide, extend tests, and verify everything." --mock
   ```

6. Show the final `OK` test result and `diff_workspace` output.
7. If using the optional Gradio frontend, show that it calls the same backend
   agent and streams the step-by-step run log, final files, and transcript.
8. Mention that real model mode uses `OPENAI_API_KEY` from the environment and
   that credentials are never stored in the repository.

## One-Minute English Introduction

This project is a lightweight coding agent runtime. It does not train a large
language model and does not wrap an existing agent product. Instead, it calls an
OpenAI-compatible chat model and implements the agent loop by itself. The model
returns JSON actions, and the runtime parses those actions, runs local tools,
feeds observations back to the model, and stops when the task is complete or a
step limit is reached. The local tools can inspect the workspace, read and edit
files, run commands, check Python syntax, verify discovered unit tests, and show
a diff of the final changes. Each run is recorded as a JSON transcript, so the
decision process is auditable. The demo shows the agent fixing a small Python
project, adding tests, running them, and verifying the final result.
