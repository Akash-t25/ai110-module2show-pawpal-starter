# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Smarter Scheduling

PawPal+ includes four algorithmic features beyond basic priority-based scheduling:

| Feature | Where | How it works |
|---|---|---|
| **Sort by time** | `Scheduler.sort_by_time()` | Sorts tasks by preferred time slot (morning → afternoon → evening → none) using a `lambda` key on the slot string. Tasks with a concrete `pinned_start` are sorted within their slot by exact minute. |
| **Filter tasks** | `Owner.filter_tasks()` | Returns tasks matching any combination of `completed` status, `pet_name`, and `category`. Implemented as a series of list comprehensions so each filter is independent and easy to extend. |
| **Recurring tasks** | `Task.next_occurrence()` + `Pet.complete_task()` | When a task with `frequency="daily"` or `"weekly"` is marked complete, Python's `timedelta` shifts the due date forward by 1 or 7 days and appends a fresh copy to the pet's task list automatically. `"as-needed"` tasks never auto-recur. |
| **Conflict detection** | `Scheduler.detect_conflicts()` | After building the plan, checks every pair of `ScheduledEntry` items for interval overlap using `a.start < b.end AND b.start < a.end`. Returns human-readable warning strings; the plan is still produced rather than crashing. Only tasks with a `pinned_start` ("HH:MM") can produce conflicts — flexible tasks are sorted by slot, not pinned to a clock time. |

## Testing PawPal+

```bash
python -m pytest              # run all tests
python -m pytest -v           # verbose — shows each test name and pass/fail
python -m pytest tests/test_pawpal.py::TestEdgeCases   # run one class only
```

The test suite lives in [tests/test_pawpal.py](tests/test_pawpal.py) and is organised into five classes:

| Class | What it covers |
|---|---|
| `TestTask` | `mark_complete`, `priority_score`, `is_high_priority`, `next_occurrence` (daily/weekly/as-needed), `pinned_start_minute` |
| `TestPet` | `add_task` / `remove_task` counts, `needs_daily_walk`, `complete_task` with and without recurrence |
| `TestOwner` | `all_tasks` aggregation, `total_task_minutes`, `filter_tasks` (by status, pet name, category, combined) |
| `TestScheduler` | Priority ordering, time budget, completed-task exclusion, `sort_by_time`, conflict detection (overlap, adjacent, single task) |
| `TestEdgeCases` | Empty pets/owners, all-tasks-done, exact budget fit, 1-minute-over budget, `ScheduledEntry` time strings (including noon crossing), `DailyPlan.display()` output, custom day-start, `next_occurrence` field preservation and non-mutation, case-insensitive filtering |

**Confidence level: ★★★★☆ (4/5)**

The scheduler's greedy algorithm and all data-layer behaviours are well covered. The remaining gap (½ star) is integration tests that drive the Streamlit UI directly and end-to-end tests against multi-day recurring task chains.

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
