# Athena — Personal AI Assistant v0.1

A local-first, modular personal assistant for managing tasks, schedules,
memories, goals, projects, and progress reports. **v0.1 works without any AI
API key** — deterministic features never call a model and never fake
intelligence.

## Tech stack

- Python 3.9+
- [Streamlit] — interface
- [SQLite] — persistent local storage
- [Pydantic] — validation
- [pytest] — automated tests

## Install

1. Install Python (3.9 or newer) if you don't have it.
2. Clone or copy this folder, then open a terminal in it.
3. Create a virtual environment (recommended):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   pip install -r requirements-dev.txt   # for running tests
   ```

## Run the application

```powershell
streamlit run ui/app.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`).

## What v0.1 does

- **Dashboard** — today's tasks, overdue tasks, upcoming deadlines, recent progress.
- **Task manager** — create, edit, delete tasks with priority, estimated minutes,
  due date, status, and completion timestamps. Tasks survive restarts (SQLite).
- **Schedule planner** — builds a day-by-day schedule around fixed commitments,
  respecting durations, breaks, deadlines, and your availability. Conflicting
  fixed events are detected and reported; the planner never schedules over them.
- **Memory manager** — save profile facts, goals, events, and knowledge notes;
  search with timestamps and source; approve, edit, and delete memories.
- **Projects** — milestones, linked tasks, notes, status.
- **Reports** — daily and weekly reports from real database records, with facts
  separated from estimates.
- **Export / backup** — download the SQLite database, a JSON export, or a zip archive.

## AI integration

v0.1 ships with a deterministic provider (`athena/ai/base.py`). It returns a
clear "Athena AI is not configured" message and never invents answers. A future
model provider can be added by subclassing `AIProvider`; the interface supports
tool calling with validated arguments, explicit tool permissions, memory
retrieval, context limits, and error handling. Model-generated text is never
executed as code.

Set `ATHENA_AI_PROVIDER` and `ATHENA_AI_API_KEY` in a `.env` file (copy
`.env.example` to `.env`) when you add a provider. Credentials are never logged.

## Tests

```powershell
pytest
```

Tests cover persistence, task operations, memory retrieval, scheduling
conflicts, and reporting.

## Limitations (honest)

- No AI model is integrated in v0.1; AI-driven reasoning is unavailable until
  a provider is implemented and configured.
- The scheduler is a deterministic greedy planner, not an optimizing solver.
- Memory search is a simple keyword (LIKE) search, not semantic/vector search.
- No user authentication; the app assumes a single local user.
- File-level DB copy is used for backup; concurrent writers are not supported.

## Security & privacy

- Data is stored locally in SQLite by default; nothing is sent to a network
  service unless you configure an AI provider.
- Never store passwords, tokens, or private keys in memories.
- API credentials belong in environment variables (`.env`), never in source or
  the database.
- Model output is never executed as Python or shell code.

[Streamlit]: https://streamlit.io
[SQLite]: https://sqlite.org
[Pydantic]: https://docs.pydantic.dev
[pytest]: https://docs.pytest.org