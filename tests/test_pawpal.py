"""
Tests for PawPal+ core logic.

Run with:  python -m pytest
"""

from datetime import date, timedelta

import pytest
from pawpal_system import Task, Pet, Owner, Scheduler, DailyPlan, ScheduledEntry


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

class TestTask:
    def test_mark_complete_changes_status(self):
        """Calling mark_complete() should flip completed from False to True."""
        task = Task(title="Morning walk", duration_minutes=30, priority="high")
        assert task.completed is False
        task.mark_complete()
        assert task.completed is True

    def test_mark_complete_is_idempotent(self):
        """Calling mark_complete() twice should not raise and status stays True."""
        task = Task(title="Feeding", duration_minutes=10, priority="medium")
        task.mark_complete()
        task.mark_complete()
        assert task.completed is True

    def test_priority_score_high(self):
        assert Task(title="Meds", duration_minutes=5, priority="high").priority_score() == 3

    def test_priority_score_medium(self):
        assert Task(title="Play", duration_minutes=15, priority="medium").priority_score() == 2

    def test_priority_score_low(self):
        assert Task(title="Grooming", duration_minutes=20, priority="low").priority_score() == 1

    def test_is_high_priority(self):
        assert Task(title="Meds", duration_minutes=5, priority="high").is_high_priority() is True
        assert Task(title="Bath", duration_minutes=30, priority="low").is_high_priority() is False

    # -- recurrence ----------------------------------------------------------

    def test_next_occurrence_daily_shifts_by_one_day(self):
        """next_occurrence() on a daily task should return a copy due tomorrow."""
        today = date.today()
        task = Task(title="Walk", duration_minutes=30, priority="high",
                    frequency="daily", due_date=today)
        next_task = task.next_occurrence()
        assert next_task is not None
        assert next_task.due_date == today + timedelta(days=1)
        assert next_task.completed is False

    def test_next_occurrence_weekly_shifts_by_seven_days(self):
        """next_occurrence() on a weekly task should return a copy due in 7 days."""
        today = date.today()
        task = Task(title="Bath", duration_minutes=30, priority="low",
                    frequency="weekly", due_date=today)
        next_task = task.next_occurrence()
        assert next_task is not None
        assert next_task.due_date == today + timedelta(weeks=1)

    def test_next_occurrence_as_needed_returns_none(self):
        """as-needed tasks should not generate a next occurrence."""
        task = Task(title="Vet visit", duration_minutes=60, priority="high",
                    frequency="as-needed")
        assert task.next_occurrence() is None

    def test_next_occurrence_defaults_to_today_when_no_due_date(self):
        """If due_date is None, next_occurrence treats today as the base date."""
        today = date.today()
        task = Task(title="Walk", duration_minutes=30, priority="high", frequency="daily")
        next_task = task.next_occurrence()
        assert next_task is not None
        assert next_task.due_date == today + timedelta(days=1)

    # -- pinned start --------------------------------------------------------

    def test_pinned_start_minute_converts_correctly(self):
        """'09:30' should convert to 9*60+30 = 570 minutes."""
        task = Task(title="Walk", duration_minutes=30, priority="high",
                    pinned_start="09:30")
        assert task.pinned_start_minute() == 570

    def test_pinned_start_minute_none_when_unset(self):
        task = Task(title="Walk", duration_minutes=30, priority="high")
        assert task.pinned_start_minute() is None


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

class TestPet:
    def test_add_task_increases_count(self):
        """Adding a task to a Pet should increase its task list length by 1."""
        pet = Pet(name="Mochi", species="dog", age_years=3)
        assert len(pet.tasks) == 0
        pet.add_task(Task(title="Walk", duration_minutes=30, priority="high"))
        assert len(pet.tasks) == 1

    def test_add_multiple_tasks(self):
        pet = Pet(name="Luna", species="cat", age_years=5)
        for i in range(3):
            pet.add_task(Task(title=f"Task {i}", duration_minutes=10, priority="low"))
        assert len(pet.tasks) == 3

    def test_remove_task_decreases_count(self):
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk",    duration_minutes=30, priority="high"))
        pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
        pet.remove_task("Walk")
        assert len(pet.tasks) == 1
        assert pet.tasks[0].title == "Feeding"

    def test_remove_nonexistent_task_is_noop(self):
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk", duration_minutes=30, priority="high"))
        pet.remove_task("Nonexistent")
        assert len(pet.tasks) == 1

    def test_dog_needs_daily_walk(self):
        assert Pet(name="Rex", species="dog", age_years=2).needs_daily_walk() is True

    def test_cat_does_not_need_daily_walk(self):
        assert Pet(name="Luna", species="cat", age_years=4).needs_daily_walk() is False

    # -- complete_task / recurrence ------------------------------------------

    def test_complete_task_marks_task_done(self):
        """complete_task() should mark the named task as completed."""
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk", duration_minutes=30, priority="high", frequency="daily"))
        pet.complete_task("Walk")
        assert pet.tasks[0].completed is True

    def test_complete_daily_task_appends_next_occurrence(self):
        """Completing a daily task should add a new pending task to the pet's list."""
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk", duration_minutes=30, priority="high", frequency="daily"))
        assert len(pet.tasks) == 1
        pet.complete_task("Walk")
        assert len(pet.tasks) == 2
        assert pet.tasks[1].completed is False

    def test_complete_as_needed_task_does_not_append(self):
        """Completing an as-needed task should NOT create a next occurrence."""
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Vet", duration_minutes=60, priority="high",
                          frequency="as-needed"))
        pet.complete_task("Vet")
        assert len(pet.tasks) == 1   # no new task added

    def test_complete_task_returns_none_for_unknown_title(self):
        """Completing a task that doesn't exist should return None silently."""
        pet = Pet(name="Mochi", species="dog", age_years=3)
        result = pet.complete_task("Nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------

class TestOwner:
    def test_add_pet_increases_count(self):
        owner = Owner(name="Jordan", available_minutes=120)
        assert len(owner.pets) == 0
        owner.add_pet(Pet(name="Mochi", species="dog", age_years=3))
        assert len(owner.pets) == 1

    def test_all_tasks_aggregates_across_pets(self):
        owner = Owner(name="Jordan", available_minutes=120)
        dog = Pet(name="Mochi", species="dog", age_years=3)
        cat = Pet(name="Luna",  species="cat", age_years=5)
        dog.add_task(Task(title="Walk",    duration_minutes=30, priority="high"))
        dog.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
        cat.add_task(Task(title="Play",    duration_minutes=15, priority="medium"))
        owner.add_pet(dog)
        owner.add_pet(cat)
        assert len(owner.all_tasks()) == 3

    def test_total_task_minutes_sums_correctly(self):
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk",    duration_minutes=30, priority="high"))
        pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
        owner.add_pet(pet)
        assert owner.total_task_minutes() == 40

    # -- filter_tasks --------------------------------------------------------

    def test_filter_tasks_by_completed_false(self):
        """filter_tasks(completed=False) should return only pending tasks."""
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        done = Task(title="Walk",    duration_minutes=30, priority="high")
        done.mark_complete()
        pending = Task(title="Feeding", duration_minutes=10, priority="high")
        pet.add_task(done)
        pet.add_task(pending)
        owner.add_pet(pet)
        result = owner.filter_tasks(completed=False)
        assert len(result) == 1
        assert result[0].title == "Feeding"

    def test_filter_tasks_by_completed_true(self):
        """filter_tasks(completed=True) should return only completed tasks."""
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        done = Task(title="Walk", duration_minutes=30, priority="high")
        done.mark_complete()
        pet.add_task(done)
        pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
        owner.add_pet(pet)
        result = owner.filter_tasks(completed=True)
        assert len(result) == 1
        assert result[0].title == "Walk"

    def test_filter_tasks_by_pet_name(self):
        """filter_tasks(pet_name='Mochi') should return only Mochi's tasks."""
        owner = Owner(name="Jordan", available_minutes=120)
        dog = Pet(name="Mochi", species="dog", age_years=3)
        cat = Pet(name="Luna",  species="cat", age_years=5)
        dog.add_task(Task(title="Walk", duration_minutes=30, priority="high"))
        cat.add_task(Task(title="Play", duration_minutes=15, priority="medium"))
        owner.add_pet(dog)
        owner.add_pet(cat)
        result = owner.filter_tasks(pet_name="Mochi")
        assert len(result) == 1
        assert result[0].title == "Walk"

    def test_filter_tasks_by_category(self):
        """filter_tasks(category='medical') should return only medical tasks."""
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Meds",    duration_minutes=5,  priority="high", category="medical"))
        pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high", category="feeding"))
        owner.add_pet(pet)
        result = owner.filter_tasks(category="medical")
        assert len(result) == 1
        assert result[0].title == "Meds"

    def test_filter_tasks_no_filters_returns_all(self):
        """Calling filter_tasks() with no args should return all tasks."""
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk",    duration_minutes=30, priority="high"))
        pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
        owner.add_pet(pet)
        assert len(owner.filter_tasks()) == 2


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

class TestScheduler:
    def _make_owner_with_tasks(self) -> Owner:
        owner = Owner(name="Jordan", available_minutes=60)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk",    duration_minutes=30, priority="high"))
        pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
        pet.add_task(Task(title="Play",    duration_minutes=15, priority="medium"))
        owner.add_pet(pet)
        return owner

    def test_generate_plan_returns_daily_plan(self):
        plan = Scheduler(self._make_owner_with_tasks()).generate_plan()
        assert isinstance(plan, DailyPlan)

    def test_scheduler_respects_time_budget(self):
        owner = self._make_owner_with_tasks()  # 60 min; tasks total 55 min
        plan = Scheduler(owner).generate_plan()
        assert plan.total_scheduled_minutes() <= owner.available_minutes

    def test_high_priority_tasks_scheduled_first(self):
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Low task",  duration_minutes=10, priority="low"))
        pet.add_task(Task(title="High task", duration_minutes=10, priority="high"))
        pet.add_task(Task(title="Med task",  duration_minutes=10, priority="medium"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan()
        titles = [e.task.title for e in plan.entries]
        assert titles.index("High task") < titles.index("Med task")
        assert titles.index("Med task")  < titles.index("Low task")

    def test_completed_tasks_not_scheduled(self):
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        done = Task(title="Walk", duration_minutes=30, priority="high")
        done.mark_complete()
        pet.add_task(done)
        pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan()
        titles = [e.task.title for e in plan.entries]
        assert "Walk" not in titles
        assert "Feeding" in titles

    def test_tasks_that_dont_fit_are_skipped(self):
        owner = Owner(name="Jordan", available_minutes=15)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk",    duration_minutes=30, priority="high"))
        pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan()
        assert "Walk" in [t.title for t in plan.skipped_tasks]

    # -- sort_by_time --------------------------------------------------------

    def test_sort_by_time_morning_before_afternoon(self):
        """sort_by_time should place morning tasks before afternoon tasks."""
        tasks = [
            Task(title="Afternoon",   duration_minutes=10, priority="low", preferred_time="afternoon"),
            Task(title="Morning",     duration_minutes=10, priority="low", preferred_time="morning"),
            Task(title="No pref",     duration_minutes=10, priority="low"),
            Task(title="Evening",     duration_minutes=10, priority="low", preferred_time="evening"),
        ]
        sorted_tasks = Scheduler.sort_by_time(tasks)
        titles = [t.title for t in sorted_tasks]
        assert titles.index("Morning")   < titles.index("Afternoon")
        assert titles.index("Afternoon") < titles.index("Evening")
        assert titles.index("Evening")   < titles.index("No pref")

    def test_sort_by_time_pinned_tasks_ordered_within_slot(self):
        """Pinned tasks in the same slot should be sorted by their start minute."""
        tasks = [
            Task(title="Late",  duration_minutes=10, priority="low",
                 preferred_time="morning", pinned_start="10:00"),
            Task(title="Early", duration_minutes=10, priority="low",
                 preferred_time="morning", pinned_start="08:00"),
        ]
        sorted_tasks = Scheduler.sort_by_time(tasks)
        assert sorted_tasks[0].title == "Early"
        assert sorted_tasks[1].title == "Late"

    # -- detect_conflicts ----------------------------------------------------

    def test_detect_conflicts_finds_overlap(self):
        """detect_conflicts should return a warning when two entries overlap."""
        owner = Owner(name="Jordan", available_minutes=240)
        pet = Pet(name="Rex", species="dog", age_years=2)
        # Both pinned to 9:00 AM – guaranteed overlap
        pet.add_task(Task(title="Vet",      duration_minutes=60, priority="high",
                          pinned_start="09:00"))
        pet.add_task(Task(title="Training", duration_minutes=45, priority="medium",
                          pinned_start="09:30"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan()
        assert len(plan.conflicts) > 0
        assert any("Vet" in w and "Training" in w for w in plan.conflicts)

    def test_detect_conflicts_no_overlap_when_sequential(self):
        """Sequential tasks (greedy schedule) should produce zero conflicts."""
        owner = self._make_owner_with_tasks()
        plan = Scheduler(owner).generate_plan()
        assert plan.conflicts == []

    def test_detect_conflicts_adjacent_tasks_not_flagged(self):
        """Tasks that share an endpoint but don't overlap should not conflict."""
        owner = Owner(name="Jordan", available_minutes=240)
        pet = Pet(name="Rex", species="dog", age_years=2)
        # 9:00–9:30 then 9:30–10:00 — adjacent, not overlapping
        pet.add_task(Task(title="Walk",    duration_minutes=30, priority="high",
                          pinned_start="09:00"))
        pet.add_task(Task(title="Feeding", duration_minutes=30, priority="high",
                          pinned_start="09:30"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan()
        assert plan.conflicts == []


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Boundary conditions and less-obvious scenarios."""

    # -- empty / zero states -------------------------------------------------

    def test_pet_with_no_tasks_produces_empty_plan(self):
        """A pet registered with no tasks should result in an empty schedule."""
        owner = Owner(name="Jordan", available_minutes=120)
        owner.add_pet(Pet(name="Mochi", species="dog", age_years=3))
        plan = Scheduler(owner).generate_plan()
        assert plan.entries == []
        assert plan.skipped_tasks == []
        assert plan.conflicts == []

    def test_owner_with_no_pets_produces_empty_plan(self):
        """An owner with no pets registered should produce an empty schedule."""
        owner = Owner(name="Jordan", available_minutes=120)
        plan = Scheduler(owner).generate_plan()
        assert plan.entries == []

    def test_all_tasks_completed_produces_empty_schedule(self):
        """If every task is already done, nothing should be scheduled."""
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        for title in ("Walk", "Feeding", "Play"):
            task = Task(title=title, duration_minutes=10, priority="high")
            task.mark_complete()
            pet.add_task(task)
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan()
        assert plan.entries == []

    def test_daily_plan_total_minutes_zero_when_no_entries(self):
        """total_scheduled_minutes() should return 0 for an empty plan."""
        assert DailyPlan().total_scheduled_minutes() == 0

    def test_all_tasks_returns_empty_list_for_owner_with_no_pets(self):
        """Owner.all_tasks() should return [] when no pets are registered."""
        assert Owner(name="Jordan", available_minutes=60).all_tasks() == []

    def test_sort_by_time_empty_list_returns_empty(self):
        """sort_by_time([]) should not raise and should return []."""
        assert Scheduler.sort_by_time([]) == []

    # -- exact boundary: task fills remaining budget exactly -----------------

    def test_task_that_exactly_fills_budget_is_scheduled(self):
        """A single task whose duration equals available_minutes must be scheduled."""
        owner = Owner(name="Jordan", available_minutes=30)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk", duration_minutes=30, priority="high"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan()
        assert len(plan.entries) == 1
        assert plan.skipped_tasks == []

    def test_task_one_minute_over_budget_is_skipped(self):
        """A task 1 minute over the budget must land in skipped_tasks."""
        owner = Owner(name="Jordan", available_minutes=29)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk", duration_minutes=30, priority="high"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan()
        assert plan.entries == []
        assert len(plan.skipped_tasks) == 1

    # -- ScheduledEntry helpers ----------------------------------------------

    def test_scheduled_entry_end_minute(self):
        """end_minute() should equal start_minute + task.duration_minutes."""
        task  = Task(title="Walk", duration_minutes=30, priority="high")
        entry = ScheduledEntry(task=task, start_minute=480, reason="test")
        assert entry.end_minute() == 510

    def test_scheduled_entry_start_time_str_format(self):
        """start_time_str() for minute 480 (8:00 AM) should return '8:00 AM'."""
        task  = Task(title="Walk", duration_minutes=30, priority="high")
        entry = ScheduledEntry(task=task, start_minute=480, reason="test")
        assert entry.start_time_str() == "8:00 AM"

    def test_scheduled_entry_end_time_str_format(self):
        """end_time_str() for an entry starting at 480 with 30 min = '8:30 AM'."""
        task  = Task(title="Walk", duration_minutes=30, priority="high")
        entry = ScheduledEntry(task=task, start_minute=480, reason="test")
        assert entry.end_time_str() == "8:30 AM"

    def test_scheduled_entry_crosses_noon(self):
        """An entry starting at 11:45 AM and lasting 30 min ends at 12:15 PM."""
        task  = Task(title="Feeding", duration_minutes=30, priority="high")
        entry = ScheduledEntry(task=task, start_minute=11 * 60 + 45, reason="test")
        assert entry.end_time_str() == "12:15 PM"

    # -- DailyPlan.display() smoke test --------------------------------------

    def test_daily_plan_display_returns_string(self):
        """display() should return a non-empty string regardless of content."""
        plan = DailyPlan()
        output = plan.display()
        assert isinstance(output, str)
        assert len(output) > 0

    def test_daily_plan_display_includes_task_title(self):
        """display() should include the task title in its output."""
        task  = Task(title="Morning walk", duration_minutes=30, priority="high")
        entry = ScheduledEntry(task=task, start_minute=480, reason="High priority")
        plan  = DailyPlan()
        plan.add_entry(entry)
        assert "Morning walk" in plan.display()

    def test_daily_plan_display_includes_conflict_warning(self):
        """display() should include conflict text when conflicts exist."""
        plan = DailyPlan()
        plan.conflicts = ["⚠ CONFLICT: 'A' overlaps 'B'"]
        assert "CONFLICT" in plan.display()

    # -- Scheduler custom start time -----------------------------------------

    def test_custom_day_start_minute_respected(self):
        """First scheduled entry should start at the custom day_start_minute."""
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk", duration_minutes=30, priority="high"))
        owner.add_pet(pet)
        plan = Scheduler(owner, day_start_minute=7 * 60).generate_plan()  # 7:00 AM
        assert plan.entries[0].start_minute == 7 * 60

    # -- next_occurrence preserves fields ------------------------------------

    def test_next_occurrence_preserves_task_metadata(self):
        """next_occurrence() should copy title, duration, priority, and category."""
        task = Task(
            title="Meds", duration_minutes=5, priority="high",
            category="medical", frequency="daily", due_date=date.today(),
        )
        next_task = task.next_occurrence()
        assert next_task is not None
        assert next_task.title    == task.title
        assert next_task.duration_minutes == task.duration_minutes
        assert next_task.priority == task.priority
        assert next_task.category == task.category
        assert next_task.frequency == task.frequency

    def test_next_occurrence_does_not_mutate_original(self):
        """next_occurrence() must not change the original task's due_date."""
        today = date.today()
        task = Task(title="Walk", duration_minutes=30, priority="high",
                    frequency="daily", due_date=today)
        task.next_occurrence()
        assert task.due_date == today   # original unchanged

    # -- complete_task idempotency -------------------------------------------

    def test_complete_task_no_pending_match_returns_none(self):
        """complete_task() should return None when no pending task with that title exists.

        Using frequency='as-needed' means no next occurrence is ever created,
        so after completing the task once there is no pending 'Vet' left to complete.
        """
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Vet", duration_minutes=60, priority="high",
                          frequency="as-needed"))
        pet.complete_task("Vet")            # marks it done; no next occurrence added
        result = pet.complete_task("Vet")   # no pending 'Vet' task exists → no-op
        assert result is None
        assert len(pet.tasks) == 1          # still just the one completed task

    # -- filter_tasks combined and edge filters ------------------------------

    def test_filter_tasks_combined_pet_and_category(self):
        """Combining pet_name and category should only return matching tasks."""
        owner = Owner(name="Jordan", available_minutes=120)
        dog = Pet(name="Mochi", species="dog", age_years=3)
        cat = Pet(name="Luna",  species="cat", age_years=5)
        dog.add_task(Task(title="Meds", duration_minutes=5,  priority="high", category="medical"))
        dog.add_task(Task(title="Walk", duration_minutes=30, priority="high", category="exercise"))
        cat.add_task(Task(title="Cat meds", duration_minutes=5, priority="high", category="medical"))
        owner.add_pet(dog)
        owner.add_pet(cat)
        result = owner.filter_tasks(pet_name="Mochi", category="medical")
        assert len(result) == 1
        assert result[0].title == "Meds"

    def test_filter_tasks_nonexistent_pet_returns_empty(self):
        """Filtering by a pet name that doesn't exist should return []."""
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk", duration_minutes=30, priority="high"))
        owner.add_pet(pet)
        assert owner.filter_tasks(pet_name="Ghost") == []

    def test_filter_tasks_pet_name_case_insensitive(self):
        """pet_name filter should match regardless of capitalisation."""
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk", duration_minutes=30, priority="high"))
        owner.add_pet(pet)
        assert len(owner.filter_tasks(pet_name="mochi")) == 1
        assert len(owner.filter_tasks(pet_name="MOCHI")) == 1

    # -- conflict detection edge cases ---------------------------------------

    def test_detect_conflicts_exact_same_start_time(self):
        """Two tasks pinned to the exact same minute must produce a conflict."""
        owner = Owner(name="Jordan", available_minutes=240)
        pet = Pet(name="Rex", species="dog", age_years=2)
        pet.add_task(Task(title="Task A", duration_minutes=30, priority="high",
                          pinned_start="09:00"))
        pet.add_task(Task(title="Task B", duration_minutes=30, priority="high",
                          pinned_start="09:00"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan()
        assert len(plan.conflicts) >= 1

    def test_detect_conflicts_returns_empty_for_single_task(self):
        """A plan with only one task can never have a conflict."""
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Rex", species="dog", age_years=2)
        pet.add_task(Task(title="Walk", duration_minutes=30, priority="high",
                          pinned_start="09:00"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan()
        assert plan.conflicts == []

    # -- remove_pet ----------------------------------------------------------

    def test_remove_pet_reduces_count(self):
        """remove_pet() should decrease the owner's pet list by 1."""
        owner = Owner(name="Jordan", available_minutes=120)
        owner.add_pet(Pet(name="Mochi", species="dog", age_years=3))
        owner.add_pet(Pet(name="Luna",  species="cat", age_years=5))
        assert len(owner.pets) == 2
        owner.remove_pet("Mochi")
        assert len(owner.pets) == 1
        assert owner.pets[0].name == "Luna"

    def test_remove_nonexistent_pet_is_noop(self):
        """Removing a pet that was never added should not raise or change the list."""
        owner = Owner(name="Jordan", available_minutes=120)
        owner.add_pet(Pet(name="Mochi", species="dog", age_years=3))
        owner.remove_pet("Ghost")
        assert len(owner.pets) == 1
