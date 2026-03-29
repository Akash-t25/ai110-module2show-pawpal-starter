"""
Tests for PawPal+ core logic.

Run with:  python -m pytest
"""

import pytest
from pawpal_system import Task, Pet, Owner, Scheduler, DailyPlan


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
        task = Task(title="Meds", duration_minutes=5, priority="high")
        assert task.priority_score() == 3

    def test_priority_score_medium(self):
        task = Task(title="Play", duration_minutes=15, priority="medium")
        assert task.priority_score() == 2

    def test_priority_score_low(self):
        task = Task(title="Grooming", duration_minutes=20, priority="low")
        assert task.priority_score() == 1

    def test_is_high_priority(self):
        high = Task(title="Meds", duration_minutes=5, priority="high")
        low  = Task(title="Bath", duration_minutes=30, priority="low")
        assert high.is_high_priority() is True
        assert low.is_high_priority() is False


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
        """Adding three tasks should result in a task list of length 3."""
        pet = Pet(name="Luna", species="cat", age_years=5)
        for i in range(3):
            pet.add_task(Task(title=f"Task {i}", duration_minutes=10, priority="low"))
        assert len(pet.tasks) == 3

    def test_remove_task_decreases_count(self):
        """remove_task() should reduce the task count by 1."""
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk", duration_minutes=30, priority="high"))
        pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
        pet.remove_task("Walk")
        assert len(pet.tasks) == 1
        assert pet.tasks[0].title == "Feeding"

    def test_remove_nonexistent_task_is_noop(self):
        """Removing a task that doesn't exist should not raise or change the list."""
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk", duration_minutes=30, priority="high"))
        pet.remove_task("Nonexistent")
        assert len(pet.tasks) == 1

    def test_dog_needs_daily_walk(self):
        dog = Pet(name="Rex", species="dog", age_years=2)
        assert dog.needs_daily_walk() is True

    def test_cat_does_not_need_daily_walk(self):
        cat = Pet(name="Luna", species="cat", age_years=4)
        assert cat.needs_daily_walk() is False


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------

class TestOwner:
    def test_add_pet_increases_count(self):
        """add_pet() should increase the owner's pet list length by 1."""
        owner = Owner(name="Jordan", available_minutes=120)
        assert len(owner.pets) == 0
        owner.add_pet(Pet(name="Mochi", species="dog", age_years=3))
        assert len(owner.pets) == 1

    def test_all_tasks_aggregates_across_pets(self):
        """all_tasks() should return tasks from every pet combined."""
        owner = Owner(name="Jordan", available_minutes=120)
        dog = Pet(name="Mochi", species="dog", age_years=3)
        cat = Pet(name="Luna", species="cat", age_years=5)
        dog.add_task(Task(title="Walk", duration_minutes=30, priority="high"))
        dog.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
        cat.add_task(Task(title="Play", duration_minutes=15, priority="medium"))
        owner.add_pet(dog)
        owner.add_pet(cat)
        assert len(owner.all_tasks()) == 3

    def test_total_task_minutes_sums_correctly(self):
        """total_task_minutes() should equal the sum of all tasks' durations."""
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk", duration_minutes=30, priority="high"))
        pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
        owner.add_pet(pet)
        assert owner.total_task_minutes() == 40


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
        """generate_plan() should return a DailyPlan instance."""
        owner = self._make_owner_with_tasks()
        plan = Scheduler(owner).generate_plan()
        assert isinstance(plan, DailyPlan)

    def test_scheduler_respects_time_budget(self):
        """No plan should exceed the owner's available_minutes."""
        owner = self._make_owner_with_tasks()  # 60 min available; tasks total 55 min
        plan = Scheduler(owner).generate_plan()
        assert plan.total_scheduled_minutes() <= owner.available_minutes

    def test_high_priority_tasks_scheduled_first(self):
        """High-priority tasks should appear before lower-priority ones in the plan."""
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Low task",  duration_minutes=10, priority="low"))
        pet.add_task(Task(title="High task", duration_minutes=10, priority="high"))
        pet.add_task(Task(title="Med task",  duration_minutes=10, priority="medium"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan()
        titles = [e.task.title for e in plan.entries]
        assert titles.index("High task") < titles.index("Med task")
        assert titles.index("Med task") < titles.index("Low task")

    def test_completed_tasks_not_scheduled(self):
        """Tasks already marked complete should be excluded from the plan."""
        owner = Owner(name="Jordan", available_minutes=120)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        done_task = Task(title="Walk", duration_minutes=30, priority="high")
        done_task.mark_complete()
        pet.add_task(done_task)
        pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan()
        scheduled_titles = [e.task.title for e in plan.entries]
        assert "Walk" not in scheduled_titles
        assert "Feeding" in scheduled_titles

    def test_tasks_that_dont_fit_are_skipped(self):
        """Tasks that exceed the remaining time budget should land in skipped_tasks."""
        owner = Owner(name="Jordan", available_minutes=15)
        pet = Pet(name="Mochi", species="dog", age_years=3)
        pet.add_task(Task(title="Walk",    duration_minutes=30, priority="high"))
        pet.add_task(Task(title="Feeding", duration_minutes=10, priority="high"))
        owner.add_pet(pet)
        plan = Scheduler(owner).generate_plan()
        skipped_titles = [t.title for t in plan.skipped_tasks]
        assert "Walk" in skipped_titles
