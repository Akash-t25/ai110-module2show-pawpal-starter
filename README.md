# PawPal+ (Module 2 Project)

A Streamlit pet-care planning app that helps a busy owner stay consistent with daily routines for multiple pets. The backend is pure Python (`pawpal_system.py`); the frontend is Streamlit (`app.py`).

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

## Features

| Feature | Description |
|---|---|
| **Multi-pet support** | Register unlimited pets; each pet owns its own independent task list. |
| **Priority scheduling** | Tasks are sorted high → medium → low priority before being placed into the day's time budget. |
| **Time-slot sorting** | `Scheduler.sort_by_time()` orders tasks by preferred slot (morning → afternoon → evening → unset) using a `lambda` sort key. |
| **Greedy time budgeting** | Scheduler fills the owner's available minutes greedily; tasks that don't fit land in a "Skipped" list with a tip. |
| **Pinned start times** | Set an exact `HH:MM` start on any task to lock it to a specific clock time (e.g., a vet appointment at 9:00 AM). |
| **Conflict detection** | After building the plan, `Scheduler.detect_conflicts()` checks every pair of entries for interval overlap (`a.start < b.end AND b.start < a.end`) and surfaces warnings in the UI. |
| **Recurring tasks** | `Task.next_occurrence()` uses Python's `timedelta` to shift a completed daily (+1 day) or weekly (+7 days) task to its next due date. Completing a task in the UI automatically appends the next occurrence. |
| **Task filtering** | `Owner.filter_tasks()` lets you narrow by completion status, pet name (case-insensitive), and category — all viewable in the Explore section before scheduling. |
| **Reasoning display** | Every scheduled entry shows a human-readable explanation of *why* it was placed (priority, preferred time, category, frequency). |

## Getting started

```bash
# 1 – clone and enter the repo
git clone https://github.com/Akash-t25/ai110-module2show-pawpal-starter.git
cd ai110-module2show-pawpal-starter

# 2 – create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3 – install dependencies
pip install -r requirements.txt

# 4 – run the app
streamlit run app.py

# 5 – run the demo script in the terminal
python3 main.py
```

## Testing PawPal+

```bash
python -m pytest              # run all 66 tests
python -m pytest -v           # verbose — shows each test name
python -m pytest tests/test_pawpal.py::TestEdgeCases   # edge cases only
```

The test suite (`tests/test_pawpal.py`) is organised into five classes:

| Class | What it covers |
|---|---|
| `TestTask` | `mark_complete`, `priority_score`, `is_high_priority`, `next_occurrence` (daily/weekly/as-needed), `pinned_start_minute` |
| `TestPet` | Add/remove task counts, `needs_daily_walk`, `complete_task` with and without recurrence |
| `TestOwner` | `all_tasks` aggregation, `total_task_minutes`, `filter_tasks` (status, pet name, category, combined) |
| `TestScheduler` | Priority ordering, time budget, completed-task exclusion, `sort_by_time`, conflict detection |
| `TestEdgeCases` | Empty pets/owners, all-tasks-done, exact budget fit, 1-minute-over, time strings, noon-crossing, `DailyPlan.display()`, field preservation, case-insensitive filter |

**Confidence level: ★★★★☆ (4/5)**

All core scheduling behaviours and edge cases are covered. Remaining gap: Streamlit UI integration tests and multi-week recurrence chain tests.

## Smarter Scheduling

PawPal+ adds four algorithmic layers beyond a basic to-do list:

| Algorithm | Location | Key technique |
|---|---|---|
| Sort by time | `Scheduler.sort_by_time()` | `sorted()` with a `lambda` key mapping slot strings to integers |
| Filter tasks | `Owner.filter_tasks()` | Chained list comprehensions over `(pet, task)` pairs |
| Recurring tasks | `Task.next_occurrence()` + `Pet.complete_task()` | `dataclasses.replace()` + `datetime.timedelta` |
| Conflict detection | `Scheduler.detect_conflicts()` | Pairwise interval overlap: `a.start < b.end AND b.start < a.end` |

## Project structure

```
pawpal_system.py   – all backend classes (Task, Pet, Owner, Scheduler, DailyPlan)
app.py             – Streamlit UI (Owner setup, pet/task management, schedule view)
main.py            – terminal demo script (sorting, filtering, recurrence, conflicts)
tests/
  test_pawpal.py   – 66 automated pytest tests
reflection.md      – design journal and AI-collaboration notes
```

## Suggested workflow (for developers)

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
