"""
PawPal+ – Streamlit UI

app.py is the bridge between the user interface and the logic layer
(pawpal_system.py).  All persistent state lives in st.session_state so
that objects survive Streamlit's top-to-bottom re-runs.
"""

import streamlit as st

# ── Step 1: import the logic layer ──────────────────────────────────────────
from pawpal_system import Owner, Pet, Task, Scheduler

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("A daily pet-care planner that works around *your* schedule.")
st.divider()

# ── Step 2: initialise session_state "vault" ─────────────────────────────────
# Only create the Owner once; subsequent re-runs reuse the same object.
if "owner" not in st.session_state:
    st.session_state.owner = None          # not set up yet
if "schedule" not in st.session_state:
    st.session_state.schedule = None       # no plan generated yet


# ============================================================================
# Section 1 – Owner setup
# ============================================================================
st.subheader("1 · Owner setup")

with st.form("owner_form"):
    col1, col2 = st.columns(2)
    with col1:
        owner_name = st.text_input("Your name", value="Jordan")
    with col2:
        avail_hours = st.number_input(
            "Time available today (hours)", min_value=0.5, max_value=12.0,
            value=2.0, step=0.5,
        )
    submitted_owner = st.form_submit_button("Save owner")

if submitted_owner:
    avail_minutes = int(avail_hours * 60)
    if st.session_state.owner is None:
        # ── Step 3: wire UI → Owner() constructor ──────────────────────────
        st.session_state.owner = Owner(
            name=owner_name,
            available_minutes=avail_minutes,
        )
    else:
        # Update existing owner without losing pets
        st.session_state.owner.name = owner_name
        st.session_state.owner.available_minutes = avail_minutes
    st.success(f"Owner **{owner_name}** saved ({avail_minutes} min available).")

owner: Owner | None = st.session_state.owner

if owner:
    st.caption(
        f"Current owner: **{owner.name}** · "
        f"{owner.available_minutes} min available · "
        f"{len(owner.pets)} pet(s) registered"
    )
else:
    st.info("Fill in your name and available time, then click **Save owner** to get started.")

st.divider()


# ============================================================================
# Section 2 – Pets
# ============================================================================
st.subheader("2 · Your pets")

if owner is None:
    st.warning("Set up an owner first.")
else:
    # ── Add-pet form ─────────────────────────────────────────────────────────
    with st.expander("➕ Add a pet", expanded=len(owner.pets) == 0):
        with st.form("add_pet_form"):
            c1, c2 = st.columns(2)
            with c1:
                pet_name    = st.text_input("Pet name", value="Mochi")
                pet_species = st.selectbox("Species", ["dog", "cat", "other"])
            with c2:
                pet_age   = st.number_input("Age (years)", min_value=0.0, max_value=30.0, value=3.0, step=0.5)
                pet_breed = st.text_input("Breed (optional)", value="")
            submitted_pet = st.form_submit_button("Add pet")

        if submitted_pet:
            # Guard: don't add a duplicate name
            existing_names = [p.name.lower() for p in owner.pets]
            if pet_name.strip().lower() in existing_names:
                st.warning(f"A pet named **{pet_name}** is already registered.")
            else:
                # ── Step 3: wire UI → owner.add_pet() ────────────────────────
                new_pet = Pet(
                    name=pet_name.strip(),
                    species=pet_species,
                    age_years=pet_age,
                    breed=pet_breed.strip() or "unknown",
                )
                owner.add_pet(new_pet)
                st.success(f"**{new_pet.name}** added!")
                st.session_state.schedule = None   # stale plan → reset

    # ── Pet roster ───────────────────────────────────────────────────────────
    if owner.pets:
        for pet in owner.pets:
            badge = "🐕" if pet.species == "dog" else ("🐈" if pet.species == "cat" else "🐾")
            task_count = len(pet.tasks)
            with st.expander(f"{badge} **{pet.name}** · {pet.species} · {pet.age_years:.1f} yr  ({task_count} task(s))"):

                # ── Task list for this pet ────────────────────────────────────
                if pet.tasks:
                    rows = []
                    for t in pet.tasks:
                        rows.append({
                            "Task": t.title,
                            "Min": t.duration_minutes,
                            "Priority": t.priority,
                            "Category": t.category,
                            "Preferred time": t.preferred_time or "—",
                            "Done": "✓" if t.completed else "",
                        })
                    st.table(rows)
                else:
                    st.caption("No tasks yet — add one below.")

                # ── Add-task form (per pet) ───────────────────────────────────
                with st.form(f"task_form_{pet.name}"):
                    tc1, tc2, tc3 = st.columns(3)
                    with tc1:
                        task_title    = st.text_input("Task title", value="Morning walk", key=f"tt_{pet.name}")
                        task_category = st.selectbox("Category",
                            ["general", "exercise", "feeding", "medical", "grooming"],
                            key=f"cat_{pet.name}")
                    with tc2:
                        task_duration = st.number_input("Duration (min)", min_value=1, max_value=240,
                            value=20, key=f"dur_{pet.name}")
                        task_freq     = st.selectbox("Frequency",
                            ["daily", "weekly", "as-needed"],
                            key=f"freq_{pet.name}")
                    with tc3:
                        task_priority = st.selectbox("Priority", ["high", "medium", "low"],
                            key=f"pri_{pet.name}")
                        task_pref_time = st.selectbox("Preferred time",
                            ["(none)", "morning", "afternoon", "evening"],
                            key=f"pt_{pet.name}")

                    submitted_task = st.form_submit_button(f"Add task to {pet.name}")

                if submitted_task:
                    # ── Step 3: wire UI → pet.add_task() ─────────────────────
                    new_task = Task(
                        title=task_title.strip(),
                        duration_minutes=int(task_duration),
                        priority=task_priority,
                        category=task_category,
                        preferred_time=None if task_pref_time == "(none)" else task_pref_time,
                        frequency=task_freq,
                    )
                    pet.add_task(new_task)
                    st.success(f"Task **{new_task.title}** added to {pet.name}.")
                    st.session_state.schedule = None   # stale plan → reset
                    st.rerun()

                # ── Remove-pet button ─────────────────────────────────────────
                if st.button(f"Remove {pet.name}", key=f"rm_{pet.name}"):
                    owner.remove_pet(pet.name)
                    st.session_state.schedule = None
                    st.rerun()
    else:
        st.info("No pets yet. Use the form above to add one.")

st.divider()


# ============================================================================
# Section 3 – Generate schedule
# ============================================================================
st.subheader("3 · Generate today's schedule")

if owner is None:
    st.warning("Set up an owner first.")
elif not owner.pets:
    st.warning("Add at least one pet with tasks.")
elif owner.total_task_minutes() == 0:
    st.warning("Add at least one task to a pet before scheduling.")
else:
    total_mins = owner.total_task_minutes()
    avail      = owner.available_minutes
    col_a, col_b = st.columns(2)
    col_a.metric("Total task time", f"{total_mins} min")
    col_b.metric("Time available",  f"{avail} min",
                 delta=f"{avail - total_mins:+d} min",
                 delta_color="normal")

    if st.button("🗓  Generate schedule", type="primary"):
        # ── Step 3: wire UI → Scheduler.generate_plan() ──────────────────────
        scheduler = Scheduler(owner=owner)
        st.session_state.schedule = scheduler.generate_plan()

# ── Display the plan if one exists ───────────────────────────────────────────
plan = st.session_state.schedule
if plan is not None:
    st.divider()
    st.subheader("📋 Today's plan")

    if not plan.entries:
        st.error("No tasks could be scheduled within the available time.")
    else:
        for entry in plan.entries:
            status_icon = "✅" if entry.task.completed else "🔲"
            with st.container(border=True):
                left, right = st.columns([4, 1])
                with left:
                    st.markdown(
                        f"**{status_icon} {entry.task.title}**  "
                        f"· {entry.start_time_str()} – {entry.end_time_str()}"
                    )
                    st.caption(
                        f"{entry.task.duration_minutes} min  |  "
                        f"{entry.task.priority} priority  |  "
                        f"category: {entry.task.category}  |  "
                        f"↳ _{entry.reason}_"
                    )
                with right:
                    if not entry.task.completed:
                        if st.button("Mark done", key=f"done_{id(entry.task)}"):
                            entry.task.mark_complete()
                            st.rerun()

    if plan.skipped_tasks:
        with st.expander(f"⚠️  {len(plan.skipped_tasks)} task(s) skipped (didn't fit)"):
            for t in plan.skipped_tasks:
                st.write(f"- **{t.title}** ({t.duration_minutes} min, {t.priority} priority)")

    st.info(plan.summary)
