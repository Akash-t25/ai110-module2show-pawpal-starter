"""
PawPal+ – backend logic layer.

Class hierarchy
---------------
Task          – a single care activity (dataclass)
Pet           – an animal with its own task list (dataclass)
Owner         – manages multiple pets; aggregates and filters tasks
ScheduledEntry– one task placed on the day's timeline (dataclass)
DailyPlan     – the ordered schedule produced by Scheduler
Scheduler     – sorts, filters, detects conflicts, and assigns start times

Phase 3 additions
-----------------
* Task.pinned_start      – optional "HH:MM" field that locks a task to an exact time
* Task.due_date          – optional date; used by next_occurrence() for recurrence
* Task.next_occurrence() – returns a fresh copy shifted by frequency (daily/weekly)
* Pet.complete_task()    – marks a task done and auto-appends its next occurrence
* Owner.filter_tasks()   – filters by completion status, pet name, and/or category
* Scheduler.sort_by_time()    – public static method: sort tasks by time slot / pinned start
* Scheduler.detect_conflicts()– returns warning strings for overlapping scheduled entries
* generate_plan()        – now supports pinned tasks and attaches conflict warnings
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _fmt_minute(minute: int) -> str:
    """Convert minutes-from-midnight to a readable 'H:MM AM/PM' string."""
    hours = minute // 60
    mins  = minute % 60
    period = "AM" if hours < 12 else "PM"
    h = hours % 12 or 12
    return f"{h}:{mins:02d} {period}"


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single pet-care activity with scheduling metadata and completion state."""

    title: str
    duration_minutes: int
    priority: str                        # "low" | "medium" | "high"
    category: str = "general"            # "exercise"|"feeding"|"medical"|"grooming"|"general"
    preferred_time: Optional[str] = None # "morning" | "afternoon" | "evening" | None
    frequency: str = "daily"             # "daily" | "weekly" | "as-needed"
    completed: bool = False
    due_date: Optional[date] = None      # date this task is next due; None = today
    pinned_start: Optional[str] = None   # "HH:MM" – lock task to an exact start time

    # -- completion ----------------------------------------------------------

    def mark_complete(self) -> None:
        """Mark this task as done for today."""
        self.completed = True

    # -- recurrence ----------------------------------------------------------

    def next_occurrence(self) -> Optional[Task]:
        """Return a new Task reset for the next due date, or None for as-needed tasks.

        Uses Python's timedelta so 'daily' shifts by 1 day and 'weekly' by 7 days.
        """
        if self.frequency == "daily":
            base = self.due_date or date.today()
            return replace(self, completed=False, due_date=base + timedelta(days=1))
        if self.frequency == "weekly":
            base = self.due_date or date.today()
            return replace(self, completed=False, due_date=base + timedelta(weeks=1))
        return None   # "as-needed" tasks don't auto-recur

    # -- priority helpers ----------------------------------------------------

    def is_high_priority(self) -> bool:
        """Return True when this task must not be dropped from the schedule."""
        return self.priority == "high"

    def priority_score(self) -> int:
        """Map priority label to a numeric score for sorting (higher = more urgent)."""
        return {"high": 3, "medium": 2, "low": 1}.get(self.priority, 0)

    # -- pinned time helper --------------------------------------------------

    def pinned_start_minute(self) -> Optional[int]:
        """Convert the 'HH:MM' pinned_start string to minutes-from-midnight, or None."""
        if not self.pinned_start:
            return None
        h, m = self.pinned_start.split(":")
        return int(h) * 60 + int(m)


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """An animal being cared for, with its own list of care tasks."""

    name: str
    species: str          # "dog" | "cat" | "other"
    age_years: float
    breed: str = "unknown"
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a care task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, title: str) -> None:
        """Remove the first task matching the given title (no-op if not found)."""
        self.tasks = [t for t in self.tasks if t.title != title]

    def complete_task(self, title: str) -> Optional[Task]:
        """Mark a task done and, if recurring, append its next occurrence to the list.

        Returns the new Task if one was created, otherwise None.
        """
        for task in self.tasks:
            if task.title == title and not task.completed:
                task.mark_complete()
                next_task = task.next_occurrence()
                if next_task:
                    self.tasks.append(next_task)
                return next_task
        return None

    def needs_daily_walk(self) -> bool:
        """Return True if this pet typically needs at least one walk per day."""
        return self.species.lower() == "dog"

    def activity_level(self) -> str:
        """Estimate activity needs based on species and age: 'low' | 'medium' | 'high'."""
        if self.species.lower() == "dog":
            if self.age_years < 2:
                return "high"
            if self.age_years > 10:
                return "low"
            return "medium"
        if self.species.lower() == "cat":
            return "low"
        return "medium"


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

class Owner:
    """The pet owner whose time budget and preferences drive the daily planner."""

    def __init__(
        self,
        name: str,
        available_minutes: int,
        preferences: Optional[list[str]] = None,
    ) -> None:
        self.name = name
        self.available_minutes = available_minutes  # total free minutes today
        self.preferences: list[str] = preferences or []
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def remove_pet(self, name: str) -> None:
        """Remove the first pet with the given name (no-op if not found)."""
        self.pets = [p for p in self.pets if p.name != name]

    def all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]

    def filter_tasks(
        self,
        completed: Optional[bool] = None,
        pet_name: Optional[str] = None,
        category: Optional[str] = None,
    ) -> list[Task]:
        """Return tasks matching all provided filters; pass None to skip a filter.

        Args:
            completed: True for done tasks, False for pending, None for both.
            pet_name:  Only return tasks belonging to this pet (case-insensitive).
            category:  Only return tasks in this category.
        """
        # Keep (pet, task) pairs so we can filter by pet name cheaply
        pairs = [(pet, task) for pet in self.pets for task in pet.tasks]

        if pet_name is not None:
            pairs = [(p, t) for p, t in pairs if p.name.lower() == pet_name.lower()]

        tasks = [t for _, t in pairs]

        if completed is not None:
            tasks = [t for t in tasks if t.completed == completed]

        if category is not None:
            tasks = [t for t in tasks if t.category == category]

        return tasks

    def total_task_minutes(self) -> int:
        """Sum the duration of all tasks across all pets."""
        return sum(t.duration_minutes for t in self.all_tasks())


# ---------------------------------------------------------------------------
# DailyPlan
# ---------------------------------------------------------------------------

@dataclass
class ScheduledEntry:
    """One task placed on the day's timeline with a start time and reasoning."""

    task: Task
    start_minute: int   # minutes from midnight (e.g. 480 = 8:00 AM)
    reason: str

    def start_time_str(self) -> str:
        """Return a formatted 'H:MM AM/PM' string for the start time."""
        return _fmt_minute(self.start_minute)

    def end_minute(self) -> int:
        """Return the minute at which this entry finishes."""
        return self.start_minute + self.task.duration_minutes

    def end_time_str(self) -> str:
        """Return a formatted 'H:MM AM/PM' string for the end time."""
        return _fmt_minute(self.end_minute())


class DailyPlan:
    """An ordered collection of ScheduledEntry items representing one day's care plan."""

    def __init__(self) -> None:
        self.entries: list[ScheduledEntry] = []
        self.skipped_tasks: list[Task] = []
        self.conflicts: list[str] = []    # populated by Scheduler.detect_conflicts()
        self.summary: str = ""

    def add_entry(self, entry: ScheduledEntry) -> None:
        """Append a scheduled entry; caller ensures chronological order."""
        self.entries.append(entry)

    def total_scheduled_minutes(self) -> int:
        """Sum the durations of all scheduled entries."""
        return sum(e.task.duration_minutes for e in self.entries)

    def display(self) -> str:
        """Return a formatted, human-readable schedule string for the terminal."""
        divider = "─" * 52
        lines = [divider, "  🐾  TODAY'S PAWPAL+ SCHEDULE", divider]

        if not self.entries:
            lines.append("  No tasks scheduled.")
        else:
            for e in self.entries:
                status = "✓" if e.task.completed else "○"
                pin    = " 📌" if e.task.pinned_start else ""
                lines.append(
                    f"  [{status}]{pin} {e.start_time_str()} – {e.end_time_str()}"
                    f"  |  {e.task.title}  ({e.task.duration_minutes} min, {e.task.priority})"
                )
                lines.append(f"       ↳ {e.reason}")

        if self.skipped_tasks:
            lines.append("")
            lines.append("  Skipped (did not fit in available time):")
            for t in self.skipped_tasks:
                lines.append(f"    - {t.title} ({t.duration_minutes} min, {t.priority} priority)")

        if self.conflicts:
            lines.append("")
            lines.append("  ⚠  Scheduling conflicts detected:")
            for w in self.conflicts:
                lines.append(f"    {w}")

        lines.append(divider)
        lines.append(
            f"  Scheduled: {len(self.entries)} tasks  |  "
            f"{self.total_scheduled_minutes()} min used  |  "
            f"{len(self.conflicts)} conflict(s)"
        )
        if self.summary:
            lines.append(f"  {self.summary}")
        lines.append(divider)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Builds a DailyPlan for an Owner by:
      1. Separating tasks into pinned (fixed start time) and unpinned.
      2. Placing pinned tasks first at their exact requested times.
      3. Sorting unpinned tasks by priority → preferred time → duration.
      4. Greedily filling remaining budget with unpinned tasks.
      5. Detecting and reporting any time-overlap conflicts.
    """

    DEFAULT_START_MINUTE = 480   # 8:00 AM

    def __init__(self, owner: Owner, day_start_minute: int = DEFAULT_START_MINUTE) -> None:
        self.owner = owner
        self.day_start_minute = day_start_minute

    # -- public API ----------------------------------------------------------

    def generate_plan(self) -> DailyPlan:
        """Produce a DailyPlan from the owner's pets' tasks, constraints, and pinned times."""
        plan = DailyPlan()
        pending = [t for t in self.owner.all_tasks() if not t.completed]

        pinned   = sorted(
            [t for t in pending if t.pinned_start],
            key=lambda t: t.pinned_start_minute(),  # type: ignore[arg-type]
        )
        unpinned = [t for t in pending if not t.pinned_start]

        # Place pinned tasks at their exact requested start times
        for task in pinned:
            plan.add_entry(ScheduledEntry(
                task=task,
                start_minute=task.pinned_start_minute(),  # type: ignore[arg-type]
                reason=self._build_reason(task) + " | pinned start",
            ))

        # Greedy fill: start after the last pinned task ends (or day start)
        minutes_used    = sum(e.task.duration_minutes for e in plan.entries)
        current_minute  = max(
            (e.end_minute() for e in plan.entries),
            default=self.day_start_minute,
        )

        for task in self._sort_tasks(unpinned):
            if self._fits_in_remaining_time(task, minutes_used):
                plan.add_entry(ScheduledEntry(
                    task=task,
                    start_minute=current_minute,
                    reason=self._build_reason(task),
                ))
                current_minute += task.duration_minutes
                minutes_used   += task.duration_minutes
            else:
                plan.skipped_tasks.append(task)

        # Sort all entries chronologically, then check for overlaps
        plan.entries.sort(key=lambda e: e.start_minute)
        plan.conflicts = self.detect_conflicts(plan.entries)

        plan.summary = (
            f"Used {minutes_used} of {self.owner.available_minutes} available minutes; "
            f"{len(plan.skipped_tasks)} task(s) skipped; "
            f"{len(plan.conflicts)} conflict(s) detected."
        )
        return plan

    @staticmethod
    def sort_by_time(tasks: list[Task]) -> list[Task]:
        """Sort tasks by preferred time slot, then by pinned start minute.

        Uses a lambda key so that 'morning' tasks come before 'afternoon',
        then 'evening', then tasks with no time preference.  Within a slot,
        tasks with a concrete pinned_start are ordered chronologically.
        """
        slot_order = {"morning": 0, "afternoon": 1, "evening": 2, None: 3}
        return sorted(
            tasks,
            key=lambda t: (
                slot_order.get(t.preferred_time, 3),
                t.pinned_start_minute() if t.pinned_start else 9999,
            ),
        )

    def detect_conflicts(self, entries: list[ScheduledEntry]) -> list[str]:
        """Return a warning string for every pair of overlapping scheduled entries.

        Two intervals [a_start, a_end) and [b_start, b_end) overlap when
        a_start < b_end AND b_start < a_end.  Returns an empty list when
        the schedule is conflict-free.
        """
        warnings: list[str] = []
        for i, a in enumerate(entries):
            for b in entries[i + 1:]:
                if a.start_minute < b.end_minute() and b.start_minute < a.end_minute():
                    warnings.append(
                        f"⚠ CONFLICT: '{a.task.title}' "
                        f"({a.start_time_str()}–{a.end_time_str()}) overlaps "
                        f"'{b.task.title}' ({b.start_time_str()}–{b.end_time_str()})"
                    )
        return warnings

    # -- private helpers -----------------------------------------------------

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered by priority (desc), preferred time slot, then duration (asc)."""
        time_order = {"morning": 0, "afternoon": 1, "evening": 2, None: 3}
        return sorted(
            tasks,
            key=lambda t: (
                -t.priority_score(),
                time_order.get(t.preferred_time, 3),
                t.duration_minutes,
            ),
        )

    def _fits_in_remaining_time(self, task: Task, minutes_used: int) -> bool:
        """Return True when the task still fits within the owner's available time budget."""
        return minutes_used + task.duration_minutes <= self.owner.available_minutes

    def _build_reason(self, task: Task) -> str:
        """Compose a short explanation of why this task was scheduled."""
        parts = [f"{task.priority.capitalize()} priority"]
        if task.preferred_time:
            parts.append(f"preferred {task.preferred_time}")
        if task.category != "general":
            parts.append(f"category: {task.category}")
        if task.frequency != "daily":
            parts.append(f"frequency: {task.frequency}")
        if task.due_date:
            parts.append(f"due {task.due_date}")
        return " | ".join(parts)
