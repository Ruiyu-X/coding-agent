# Defense Notes

## What This Project Implements

This project is a small coding agent runtime. It does not train or host a large
language model. Instead, it calls an OpenAI-compatible chat model and gives the
model local programming tools through a self-written control loop.

## Compliance Checklist

- New public Git repository: `https://github.com/Ruiyu-X/coding-agent`.
- No agent frameworks or SDKs are used.
- No hosted code execution or hosted file tools are used.
- API keys are read from environment variables only.
- Conversation history is managed in `agent/core.py`.
- Tool definitions and local execution are implemented in `agent/tools.py`.
- Model output parsing is implemented in `CodingAgent._parse_json`.
- Loop termination uses either a `final` field or `max_steps`.
- Errors are returned to the model as observations.

## Main Architecture

1. `main.py` parses the task, workspace, model mode, and step limit.
2. `CodingAgent.run` builds the message history and starts the loop.
3. The model must return one JSON object.
4. If the JSON contains `tool`, the agent executes a local tool.
5. The tool result is appended to the conversation as an observation.
6. If the JSON contains `final`, the loop stops.

## Why JSON Actions

JSON makes model decisions easy to parse and validate. It also separates the
model's reasoning text from executable action parameters, which makes the agent
loop easier to debug and record.

## Tool Design

The agent includes tools for workspace inspection, file operations, exact text
replacement, command execution, Python syntax checks, test discovery checks, and
workspace diff review.

`replace_in_file` rejects unexpected replacement counts. This reduces accidental
broad edits.

`discover_python_tests` checks not only whether tests pass, but also whether
expected new tests were actually discovered. This avoids false success when a
test is written in the wrong location.

## Known Limitation

The model can still make imperfect edits. The project handles this by exposing
errors as observations, using a step limit, saving transcripts, and providing
verification tools. The design favors a small understandable runtime over a
large framework-like system.
