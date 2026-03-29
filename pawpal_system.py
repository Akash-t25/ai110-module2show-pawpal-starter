"""
PawPal+ – backend logic layer.

Class hierarchy
---------------
Task          – a single care activity (dataclass)
Pet           – an animal with its own task list (dataclass)
Owner         – manages multiple pets; aggregates tasks for the scheduler
ScheduledEntry– one task placed on the day's timeline (dataclass)
DailyPlan     – the ordered schedule produced by Scheduler
Scheduler     – retrieves tasks from Owner's pets, sorts, and assigns start times
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _fmt_minute(minute: int) -> str:
    """Convert minutes-from-midnight to a readable 'H:MM AM/PM' string."""
    hours = minute // 60
    mins = minute % 60
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
    priority: str                   # "low" | "medium" | "high"
    category: str = "general"       # "exercise" | "feeding" | "medical" | "grooming" | "general"
    preferred_time: Optional[str] = None   # "morning" | "afternoon" | "evening" | None
    frequency: str = "daily"        # "daily" | "weekly" | "as-needed"
    completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done for today."""
        self.completed = True

    def is_high_priority(self) -> bool:
        """Return True when this task must not be dropped from the schedule."""
        return self.priority == "high"

    def priority_score(self) -> int:
        """Map priority label to a numeric score for sorting (higher = more urgent)."""
        return {"high": 3, "medium": 2, "low": 1}.get(self.priority, 0)


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
        self.summary: str = ""

    def add_entry(self, entry: ScheduledEntry) -> None:
        """Append a scheduled entry; caller ensures no time overlap."""
        self.entries.append(entry)

    def total_scheduled_minutes(self) -> int:
        """Sum the durations of all scheduled entries."""
        return sum(e.task.duration_minutes for e in self.entries)

    def display(self) -> str:
        """Return a formatted, human-readable schedule string for the terminal."""
        divider = "─" * 52
        lines = [
            divider,
            "  🐾  TODAY'S PAWPAL+ SCHEDULE",
            divider,
        ]

        if not self.entries:
            lines.append("  No tasks scheduled.")
        else:
            for e in self.entries:
                status = "✓" if e.task.completed else "○"
                lines.append(
                    f"  [{status}] {e.start_time_str()} – {e.end_time_str()}"
                    f"  |  {e.task.title}  ({e.task.duration_minutes} min, {e.task.priority})"
                )
                lines.append(f"       ↳ {e.reason}")

        if self.skipped_tasks:
            lines.append("")
            lines.append("  Skipped (did not fit in available time):")
            for t in self.skipped_tasks:
                lines.append(f"    - {t.title} ({t.duration_minutes} min, {t.priority} priority)")

        lines.append(divider)
        lines.append(f"  Scheduled: {len(self.entries)} tasks  |  {self.total_scheduled_minutes()} min used")
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
      1. Collecting all tasks from the owner's pets via owner.all_tasks().
      2. Skipping already-completed tasks.
      3. Sorting remaining tasks by priority (desc), preferred time, then duration (asc).
      4. Greedily assigning start times until the owner's time budget is exhausted.
    """

    DEFAULT_START_MINUTE = 480   # 8:00 AM

    def __init__(self, owner: Owner, day_start_minute: int = DEFAULT_START_MINUTE) -> None:
        self.owner = owner
        self.day_start_minute = day_start_minute

    def generate_plan(self) -> DailyPlan:
        """Produce a DailyPlan from the owner's pets' tasks and time constraints."""
        plan = DailyPlan()
        tasks = self._sort_tasks(self.owner.all_tasks())
        minutes_used = 0
        current_minute = self.day_start_minute

        for task in tasks:
            if task.completed:
                continue
            if self._fits_in_remaining_time(task, minutes_used):
                entry = ScheduledEntry(
                    task=task,
                    start_minute=current_minute,
                    reason=self._build_reason(task),
                )
                plan.add_entry(entry)
                current_minute += task.duration_minutes
                minutes_used += task.duration_minutes
            else:
                plan.skipped_tasks.append(task)

        plan.summary = (
            f"Used {minutes_used} of {self.owner.available_minutes} available minutes; "
            f"{len(plan.skipped_tasks)} task(s) skipped."
        )
        return plan

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
        return " | ".join(parts)
