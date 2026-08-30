# Coding Agent

A compact programming agent that interacts with an OpenAI-compatible chat model,
manages its own conversation loop, executes local tools, and completes small
coding tasks in a workspace.

This project was built for a programming-agent assessment. It intentionally
does not use agent frameworks such as LangChain, LlamaIndex, AutoGen, CrewAI,
OpenAI Agents SDK, or Claude Agent SDK.

## Features

- Self-managed agent loop with explicit step limit.
- JSON-based model action parsing.
- Local tools for listing files, reading files, writing files, appending files,
  and running shell commands.
- Workspace path guard to prevent file access outside the selected workspace.
- OpenAI-compatible API support through environment variables.
- Mock model mode for deterministic demos and tests.

## Requirements

- Python 3.10 or newer.
- An OpenAI-compatible chat completion API key for real model runs.

No third-party Python package is required.

## Quick Start

Run the built-in deterministic demo:

```bash
python main.py "Fix the calculator implementation and verify the tests." --mock
```

Run tests for the agent code:

```bash
python -m unittest discover -s tests
```

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

## Demo Task

The `demo_workspace` directory contains a small calculator project with two
intentional arithmetic bugs. The mock demo shows the agent inspecting files,
editing `calculator.py`, running `unittest`, and reporting completion.
