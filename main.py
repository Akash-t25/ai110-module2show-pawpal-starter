"""
main.py – PawPal+ demo script.

Run with:  python main.py
"""

from pawpal_system import Task, Pet, Owner, Scheduler


def main() -> None:
    # ── Owner ────────────────────────────────────────────────────────────────
    jordan = Owner(name="Jordan", available_minutes=120, preferences=["morning routines"])

    # ── Pets ─────────────────────────────────────────────────────────────────
    mochi = Pet(name="Mochi", species="dog", age_years=3, breed="Shiba Inu")
    luna  = Pet(name="Luna",  species="cat", age_years=5, breed="Domestic Shorthair")

    jordan.add_pet(mochi)
    jordan.add_pet(luna)

    # ── Tasks for Mochi (dog) ────────────────────────────────────────────────
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
    mochi.add_task(Task(
        title="Flea & tick medication",
        duration_minutes=5,
        priority="medium",
        category="medical",
        frequency="weekly",
    ))
    mochi.add_task(Task(
        title="Brushing / grooming",
        duration_minutes=20,
        priority="low",
        category="grooming",
        preferred_time="afternoon",
    ))

    # ── Tasks for Luna (cat) ─────────────────────────────────────────────────
    luna.add_task(Task(
        title="Breakfast feeding",
        duration_minutes=5,
        priority="high",
        category="feeding",
        preferred_time="morning",
    ))
    luna.add_task(Task(
        title="Play / enrichment",
        duration_minutes=15,
        priority="medium",
        category="exercise",
        preferred_time="evening",
    ))
    luna.add_task(Task(
        title="Litter box cleaning",
        duration_minutes=10,
        priority="medium",
        category="grooming",
    ))

    # ── Generate schedule ────────────────────────────────────────────────────
    print(f"\nBuilding schedule for {jordan.name} "
          f"({jordan.available_minutes} min available today) …\n")
    print(f"Pets: {', '.join(p.name for p in jordan.pets)}")
    print(f"Total task time across all pets: {jordan.total_task_minutes()} min\n")

    scheduler = Scheduler(owner=jordan, day_start_minute=8 * 60)  # start at 8:00 AM
    plan = scheduler.generate_plan()

    print(plan.display())


if __name__ == "__main__":
    main()
