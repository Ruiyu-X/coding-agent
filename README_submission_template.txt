Git repository:
https://github.com/Ruiyu-X/coding-agent

How to run:
1. Install Python 3.10 or newer.
2. Run the deterministic demo:
   python main.py "Fix the calculator implementation, add safe divide, extend tests, and verify everything." --mock
3. To use a real model, set OPENAI_API_KEY and optionally OPENAI_MODEL /
   OPENAI_BASE_URL, then run:
   python main.py "Add input validation to the demo calculator." --workspace demo_workspace

Features:
This project implements a compact coding agent without using agent frameworks
or hosted code/file tools. It manages its own conversation history, parses model
JSON actions, executes local tools, reads and writes files inside a guarded
workspace, performs focused text replacement, runs shell commands, records a
JSON transcript, reviews workspace diffs, observes errors, and iterates until it
reaches a final answer or a step limit. A mock model is included for
deterministic demonstration and tests.

Notes:
API keys must be provided through environment variables and must not be committed
to the repository, README.txt, or video.
