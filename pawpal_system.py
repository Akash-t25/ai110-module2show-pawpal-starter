"""
PawPal+ – backend logic layer.

Classes are organised as Python dataclasses (Task, Pet) plus plain classes
(Owner, Scheduler, DailyPlan) so that mutable behaviour stays easy to reason about.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Core data objects
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single pet-care action (walk, feeding, meds, grooming, etc.)."""

    title: str
    duration_minutes: int
    priority: str  # "low" | "medium" | "high"
    category: str = "general"  # e.g. "exercise", "feeding", "medical", "grooming"
    preferred_time: Optional[str] = None  # "morning" | "afternoon" | "evening" | None

    def is_high_priority(self) -> bool:
        """Return True when this task must not be dropped from the schedule."""
        ...

    def priority_score(self) -> int:
        """Map priority label to a numeric score for sorting (higher = more urgent)."""
        ...


@dataclass
class Pet:
    """Represents the animal being cared for."""

    name: str
    species: str          # "dog" | "cat" | "other"
    age_years: float
    breed: str = "unknown"

    def needs_daily_walk(self) -> bool:
        """Return True if this pet typically needs at least one walk per day."""
        ...

    def activity_level(self) -> str:
        """Estimate activity needs: 'low' | 'medium' | 'high'."""
        ...


# ---------------------------------------------------------------------------
# Owner – holds references to their pets and preferred task list
# ---------------------------------------------------------------------------

class Owner:
    """The pet owner whose schedule and preferences drive the planner."""

    def __init__(
        self,
        name: str,
        available_minutes: int,
        preferences: Optional[list[str]] = None,
    ) -> None:
        self.name = name
        self.available_minutes = available_minutes  # total minutes free today
        self.preferences: list[str] = preferences or []
        self.pets: list[Pet] = []
        self.tasks: list[Task] = []

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        ...

    def add_task(self, task: Task) -> None:
        """Add a care task to the owner's task list."""
        ...

    def remove_task(self, title: str) -> None:
        """Remove a task by title (no-op if not found)."""
        ...

    def total_task_minutes(self) -> int:
        """Sum the duration of all registered tasks."""
        ...


# ---------------------------------------------------------------------------
# DailyPlan – the output produced by the Scheduler
# ---------------------------------------------------------------------------

@dataclass
class ScheduledEntry:
    """One task placed on the day's timeline."""

    task: Task
    start_minute: int   # minutes from midnight (e.g. 480 = 8:00 AM)
    reason: str         # short human-readable explanation

    def start_time_str(self) -> str:
        """Return a formatted HH:MM string for the start time."""
        ...

    def end_minute(self) -> int:
        """Return the minute at which this entry finishes."""
        ...


class DailyPlan:
    """An ordered collection of ScheduledEntry items for one day."""

    def __init__(self) -> None:
        self.entries: list[ScheduledEntry] = []
        self.skipped_tasks: list[Task] = []   # tasks that didn't fit
        self.summary: str = ""

    def add_entry(self, entry: ScheduledEntry) -> None:
        """Append a scheduled entry (caller ensures no time overlap)."""
        ...

    def total_scheduled_minutes(self) -> int:
        """Sum of durations for all scheduled entries."""
        ...

    def display(self) -> str:
        """Return a human-readable multi-line schedule string."""
        ...


# ---------------------------------------------------------------------------
# Scheduler – core planning logic
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Builds a DailyPlan for an Owner by:
      1. Filtering tasks that fit within available time.
      2. Sorting by priority (and preferred time-of-day).
      3. Assigning start times greedily from a configurable day start.
    """

    DEFAULT_START_MINUTE = 480   # 8:00 AM

    def __init__(self, owner: Owner, day_start_minute: int = DEFAULT_START_MINUTE) -> None:
        self.owner = owner
        self.day_start_minute = day_start_minute

    def generate_plan(self) -> DailyPlan:
        """
        Entry point: produce a DailyPlan from the owner's tasks and constraints.
        """
        ...

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Return tasks ordered by priority score (descending), then duration (ascending)."""
        ...

    def _fits_in_remaining_time(self, task: Task, minutes_used: int) -> bool:
        """Return True when the task can still fit in the owner's available window."""
        ...

    def _build_reason(self, task: Task) -> str:
        """Generate a short explanation string for why a task was scheduled."""
        ...
