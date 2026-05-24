# Pulse - Agent Instructions

This document provides context and instructions for AI agents assisting with the `pulse` project.

## Project Overview

Pulse is a personal terminal-based dashboard built with Python and Textual.
It runs as a command-line utility.

## Tech Stack

- **Language:** Python 3.13+
- **Package Manager:** `uv`
- **UI Framework:** `textual`
- **CLI Framework:** `typer`
- **Terminal Styling:** `rich`
- **HTTP Client:** `httpx`
- **Linting & Formatting:** `ruff`

## Architecture & Code Organization

The source code is located in the `src/pulse/` directory.
- `main.py` contains the entry point and main application definition.
- Dashboard panels should be modular and located in `src/pulse/panels/`.
- UI elements and core app logic are decoupled for maintainability.

## Development Workflows

- Run the application: `uv run pulse`
- Format code: `uv run ruff format`
- Lint code: `uv run ruff check`

When proposing new features or debugging, keep in mind the asynchronous nature of `textual` apps.

## Agent Guidelines

- Ensure that code is properly typed.
- Prioritize updating the dashboard dynamically using Textual's reactivity features if applicable.
- Keep components modular.
