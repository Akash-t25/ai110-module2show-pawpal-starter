"""
main.py – PawPal+ demo script.

Demonstrates:
  1. Basic schedule generation (tasks added out of order, sorted automatically)
  2. Filtering tasks by pet name, completion status, and category
  3. Recurring tasks – completing a daily task auto-creates the next occurrence
  4. Conflict detection – two pinned tasks at overlapping times trigger warnings

Run with:  python3 main.py
"""

from datetime import date
from pawpal_system import Task, Pet, Owner, Scheduler


def section(title: str) -> None:
    print(f"\n{'═' * 52}")
    print(f"  {title}")
    print(f"{'═' * 52}")


# ── Owner and pets ────────────────────────────────────────────────────────────
jordan = Owner(name="Jordan", available_minutes=180, preferences=["morning routines"])

mochi = Pet(name="Mochi", species="dog", age_years=3, breed="Shiba Inu")
luna  = Pet(name="Luna",  species="cat", age_years=5, breed="Domestic Shorthair")

jordan.add_pet(mochi)
jordan.add_pet(luna)

# ── Tasks added OUT OF ORDER on purpose to prove sort_by_time works ───────────
# Evening and low-priority tasks are added first
mochi.add_task(Task(
    title="Evening walk",
    duration_minutes=20,
    priority="medium",
    category="exercise",
    preferred_time="evening",
))
luna.add_task(Task(
    title="Play / enrichment",
    duration_minutes=15,
    priority="medium",
    category="exercise",
    preferred_time="evening",
))
mochi.add_task(Task(
    title="Brushing / grooming",
    duration_minutes=20,
    priority="low",
    category="grooming",
    preferred_time="afternoon",
))
# High-priority morning tasks added last – scheduler must re-order them
mochi.add_task(Task(
    title="Morning walk",
    duration_minutes=30,
    priority="high",
    category="exercise",
    preferred_time="morning",
))
mochi.add_task(Task(
    title="Breakfast feeding",
    duration_minutes=10,
    priority="high",
    category="feeding",
    preferred_time="morning",
))
luna.add_task(Task(
    title="Breakfast feeding",
    duration_minutes=5,
    priority="high",
    category="feeding",
    preferred_time="morning",
))
mochi.add_task(Task(
    title="Flea & tick medication",
    duration_minutes=5,
    priority="medium",
    category="medical",
    frequency="weekly",
))
luna.add_task(Task(
    title="Litter box cleaning",
    duration_minutes=10,
    priority="medium",
    category="grooming",
))


# ────────────────────────────────────────────────────────────────────────────
# 1. sort_by_time demo
# ────────────────────────────────────────────────────────────────────────────
section("1 · sort_by_time — tasks reordered by time slot")

raw_order  = [t.title for t in jordan.all_tasks()]
sorted_tasks = Scheduler.sort_by_time(jordan.all_tasks())
sorted_order = [t.title for t in sorted_tasks]

print("\n  Raw insertion order:")
for i, title in enumerate(raw_order, 1):
    print(f"    {i}. {title}")

print("\n  After sort_by_time (morning → afternoon → evening → none):")
for i, t in enumerate(sorted_tasks, 1):
    slot = t.preferred_time or "no preference"
    print(f"    {i}. [{slot:12}]  {t.title}")


# ────────────────────────────────────────────────────────────────────────────
# 2. filter_tasks demo
# ────────────────────────────────────────────────────────────────────────────
section("2 · filter_tasks — by pet, status, and category")

# Mark two tasks complete so we have mixed data
mochi.tasks[0].mark_complete()   # Evening walk ← completed
luna.tasks[0].mark_complete()    # Play / enrichment ← completed

print("\n  Pending tasks only:")
for t in jordan.filter_tasks(completed=False):
    print(f"    ○ {t.title}")

print("\n  Completed tasks only:")
for t in jordan.filter_tasks(completed=True):
    print(f"    ✓ {t.title}")

print("\n  All tasks for Mochi:")
for t in jordan.filter_tasks(pet_name="Mochi"):
    status = "✓" if t.completed else "○"
    print(f"    [{status}] {t.title}")

print("\n  All feeding tasks across all pets:")
for t in jordan.filter_tasks(category="feeding"):
    print(f"    • {t.title} ({t.duration_minutes} min)")


# ────────────────────────────────────────────────────────────────────────────
# 3. Recurring tasks demo
# ────────────────────────────────────────────────────────────────────────────
section("3 · Recurring tasks — next occurrence after completion")

print(f"\n  Mochi's tasks before completing 'Breakfast feeding': {len(mochi.tasks)}")

# complete_task() marks it done AND appends the next occurrence
next_task = mochi.complete_task("Breakfast feeding")

print(f"  Mochi's tasks after completing 'Breakfast feeding':  {len(mochi.tasks)}")
if next_task:
    print(f"\n  ✅ Next occurrence auto-created:")
    print(f"     Title    : {next_task.title}")
    print(f"     Due date : {next_task.due_date}  (today {date.today()} + 1 day)")
    print(f"     Completed: {next_task.completed}")

# Weekly task demo
mochi.add_task(Task(
    title="Bath time",
    duration_minutes=30,
    priority="low",
    category="grooming",
    frequency="weekly",
    due_date=date.today(),
))
next_weekly = mochi.complete_task("Bath time")
if next_weekly:
    print(f"\n  ✅ Weekly task next occurrence:")
    print(f"     Title    : {next_weekly.title}")
    print(f"     Due date : {next_weekly.due_date}  (today {date.today()} + 7 days)")


# ────────────────────────────────────────────────────────────────────────────
# 4. Conflict detection demo
# ────────────────────────────────────────────────────────────────────────────
section("4 · Conflict detection — two pinned tasks at overlapping times")

# Build a fresh owner/pet just for the conflict demo so it stays isolated
conflict_owner = Owner(name="Jordan (conflict demo)", available_minutes=240)
rex = Pet(name="Rex", species="dog", age_years=2)
conflict_owner.add_pet(rex)

# Both tasks are pinned to 9:00 AM → they overlap → conflict warning expected
rex.add_task(Task(
    title="Vet appointment",
    duration_minutes=60,
    priority="high",
    category="medical",
    pinned_start="09:00",    # 9:00 AM – 10:00 AM
))
rex.add_task(Task(
    title="Puppy training",
    duration_minutes=45,
    priority="medium",
    category="exercise",
    pinned_start="09:30",    # 9:30 AM – 10:15 AM  ← overlaps with vet!
))
rex.add_task(Task(
    title="Afternoon walk",
    duration_minutes=30,
    priority="medium",
    category="exercise",
    preferred_time="afternoon",
))

conflict_plan = Scheduler(conflict_owner).generate_plan()
print(conflict_plan.display())


# ────────────────────────────────────────────────────────────────────────────
# 5. Final schedule for Jordan (using sort + priority together)
# ────────────────────────────────────────────────────────────────────────────
section("5 · Jordan's full daily schedule")
plan = Scheduler(jordan, day_start_minute=8 * 60).generate_plan()
print(plan.display())
