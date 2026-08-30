# Coding Agent

A compact programming agent that interacts with an OpenAI-compatible chat model,
manages its own conversation loop, executes local tools, records an auditable
transcript, and completes small coding tasks in a workspace.

This project was built for a programming-agent assessment. It intentionally
does not use agent frameworks such as LangChain, LlamaIndex, AutoGen, CrewAI,
OpenAI Agents SDK, or Claude Agent SDK.

## Features

- Self-managed agent loop with explicit step limit.
- JSON-based model action parsing.
- Local tools for workspace summary, file listing, file reading, full-file
  writing, appending, exact text replacement, command execution, and workspace
  diff review.
- Workspace path guard to prevent file access outside the selected workspace.
- Focused edit support through `replace_in_file`, which rejects ambiguous
  replacements.
- Unified diff review against the initial workspace snapshot.
- JSON transcript for every run, including decisions, tool arguments, and
  observations.
- OpenAI-compatible API support through environment variables.
- Mock model mode for deterministic demos and tests.

## Requirements

- Python 3.10 or newer.
- An OpenAI-compatible chat completion API key for real model runs.

No third-party Python package is required.

## Quick Start

Run the built-in deterministic demo:

```bash
python main.py "Fix the calculator implementation, add safe divide, extend tests, and verify everything." --mock
```

Run tests for the agent code:

```bash
python -m unittest discover -s tests
```

On Windows, use `py` instead of `python` if `python` is not in PATH.

## Run With A Real Model

Set environment variables:

```bash
set OPENAI_API_KEY=your_api_key
set OPENAI_MODEL=gpt-4o-mini
```

For an OpenAI-compatible gateway, also set:

```bash
set OPENAI_BASE_URL=https://your-compatible-endpoint/v1
```

Then run:

```bash
python main.py "Add input validation to the demo calculator." --workspace demo_workspace
```

## Design

The agent sends the model a system prompt that describes the available tools and
requires one JSON object per response. Each iteration has one of two outcomes:

1. The model selects a tool and arguments.
2. The model returns a final answer.

For tool calls, the Python program executes the tool locally, records the result,
and appends the observation back into the conversation. The loop stops when the
model returns `final` or when the maximum step count is reached.

The important implementation points are:

- Context management is implemented in `agent/core.py` by appending task,
  decisions, and observations to the message list.
- Tool definitions and local execution are implemented in `agent/tools.py`.
- Model output parsing is implemented in `CodingAgent._parse_json`.
- Termination is controlled by either a `final` JSON field or `max_steps`.
- Error handling routes invalid tools, invalid arguments, failed commands, and
  path escapes back as observations instead of crashing the whole loop.
- API keys are read only from environment variables in `agent/model_client.py`.

## Run Transcript

By default, each run writes `.agent_runs/last-run.json`. This file is ignored by
Git and can be inspected locally to see every model decision, tool call, and
tool result. Disable it with:

```bash
python main.py "your task" --transcript none
```

## Demo Task

The `demo_workspace` directory contains a small calculator project with two
intentional arithmetic bugs. The mock demo shows the agent summarizing the
workspace, inspecting files, fixing `add` and `subtract`, adding a guarded
`divide` function, extending tests, running `unittest`, reviewing the diff, and
reporting completion.
