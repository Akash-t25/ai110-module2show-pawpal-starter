"""
PawPal+ – Streamlit UI

Sections
--------
1  Owner setup          – create / update the Owner object in session_state
2  Your pets            – add pets; per-pet task management with pinned_start support
3  Explore tasks        – filter by pet / status / category; sort_by_time preview
4  Generate schedule    – call Scheduler.generate_plan(); surface conflicts & skips
"""

import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("A daily pet-care planner that works around *your* schedule.")
st.divider()

# ── Session-state vault ───────────────────────────────────────────────────────
if "owner"    not in st.session_state: st.session_state.owner    = None
if "schedule" not in st.session_state: st.session_state.schedule = None


# ============================================================================
# Section 1 – Owner setup
# ============================================================================
st.subheader("1 · Owner setup")

with st.form("owner_form"):
    c1, c2 = st.columns(2)
    with c1:
        owner_name  = st.text_input("Your name", value="Jordan")
    with c2:
        avail_hours = st.number_input("Time available today (hours)",
                                      min_value=0.5, max_value=12.0,
                                      value=2.0, step=0.5)
    submitted_owner = st.form_submit_button("Save owner")

if submitted_owner:
    avail_minutes = int(avail_hours * 60)
    if st.session_state.owner is None:
        st.session_state.owner = Owner(name=owner_name, available_minutes=avail_minutes)
    else:
        st.session_state.owner.name              = owner_name
        st.session_state.owner.available_minutes = avail_minutes
    st.success(f"Owner **{owner_name}** saved — {avail_minutes} min available today.")
    st.session_state.schedule = None

owner: Owner | None = st.session_state.owner

if owner:
    pending_count   = len(owner.filter_tasks(completed=False))
    completed_count = len(owner.filter_tasks(completed=True))
    st.caption(
        f"**{owner.name}** · {owner.available_minutes} min available · "
        f"{len(owner.pets)} pet(s) · "
        f"{pending_count} pending / {completed_count} done task(s)"
    )
else:
    st.info("Fill in your name and available time, then click **Save owner** to get started.")

st.divider()


# ============================================================================
# Section 2 – Pets & Tasks
# ============================================================================
st.subheader("2 · Your pets")

if owner is None:
    st.warning("Set up an owner first.")
else:
    # ── Add-pet form ──────────────────────────────────────────────────────────
    with st.expander("➕ Add a pet", expanded=len(owner.pets) == 0):
        with st.form("add_pet_form"):
            pc1, pc2 = st.columns(2)
            with pc1:
                pet_name    = st.text_input("Pet name", value="Mochi")
                pet_species = st.selectbox("Species", ["dog", "cat", "other"])
            with pc2:
                pet_age   = st.number_input("Age (years)", min_value=0.0,
                                            max_value=30.0, value=3.0, step=0.5)
                pet_breed = st.text_input("Breed (optional)", value="")
            submitted_pet = st.form_submit_button("Add pet")

        if submitted_pet:
            if pet_name.strip().lower() in [p.name.lower() for p in owner.pets]:
                st.warning(f"A pet named **{pet_name}** is already registered.")
            else:
                owner.add_pet(Pet(
                    name=pet_name.strip(),
                    species=pet_species,
                    age_years=pet_age,
                    breed=pet_breed.strip() or "unknown",
                ))
                st.success(f"**{pet_name.strip()}** added!")
                st.session_state.schedule = None

    # ── Pet roster ────────────────────────────────────────────────────────────
    if owner.pets:
        for pet in owner.pets:
            badge      = "🐕" if pet.species == "dog" else ("🐈" if pet.species == "cat" else "🐾")
            done_count = sum(1 for t in pet.tasks if t.completed)
            with st.expander(
                f"{badge} **{pet.name}** · {pet.species} · {pet.age_years:.1f} yr  "
                f"({len(pet.tasks)} tasks, {done_count} done)"
            ):
                # ── Task table ────────────────────────────────────────────────
                if pet.tasks:
                    rows = []
                    for t in pet.tasks:
                        freq_badge = {"daily": "🔁", "weekly": "📅", "as-needed": "🔔"}.get(t.frequency, "")
                        rows.append({
                            "Task": t.title,
                            "Min":  t.duration_minutes,
                            "Priority":  t.priority,
                            "Category":  t.category,
                            "Time pref": t.preferred_time or "—",
                            "Pinned":    t.pinned_start or "—",
                            "Freq":      freq_badge,
                            "Done":      "✓" if t.completed else "",
                        })
                    st.table(rows)
                else:
                    st.caption("No tasks yet — add one below.")

                # ── Add-task form ─────────────────────────────────────────────
                with st.form(f"task_form_{pet.name}"):
                    tc1, tc2, tc3 = st.columns(3)
                    with tc1:
                        task_title    = st.text_input("Task title", value="Morning walk",
                                                      key=f"tt_{pet.name}")
                        task_category = st.selectbox("Category",
                            ["general", "exercise", "feeding", "medical", "grooming"],
                            key=f"cat_{pet.name}")
                    with tc2:
                        task_duration  = st.number_input("Duration (min)", min_value=1,
                                                         max_value=240, value=20,
                                                         key=f"dur_{pet.name}")
                        task_freq      = st.selectbox("Frequency",
                            ["daily", "weekly", "as-needed"], key=f"freq_{pet.name}")
                    with tc3:
                        task_priority  = st.selectbox("Priority", ["high", "medium", "low"],
                                                      key=f"pri_{pet.name}")
                        task_pref_time = st.selectbox("Preferred time",
                            ["(none)", "morning", "afternoon", "evening"],
                            key=f"pt_{pet.name}")

                    task_pinned = st.text_input(
                        'Pinned start (HH:MM, optional — locks to exact clock time)',
                        value="", placeholder="e.g. 09:00", key=f"pin_{pet.name}",
                    )
                    submitted_task = st.form_submit_button(f"Add task to {pet.name}")

                if submitted_task:
                    pinned_val = task_pinned.strip() or None
                    pet.add_task(Task(
                        title=task_title.strip(),
                        duration_minutes=int(task_duration),
                        priority=task_priority,
                        category=task_category,
                        preferred_time=None if task_pref_time == "(none)" else task_pref_time,
                        frequency=task_freq,
                        pinned_start=pinned_val,
                    ))
                    st.success(f"Task **{task_title.strip()}** added to {pet.name}.")
                    st.session_state.schedule = None
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
# Section 3 – Explore tasks (filter + sort_by_time preview)
# ============================================================================
st.subheader("3 · Explore tasks")

if owner and owner.all_tasks():
    ef1, ef2, ef3 = st.columns(3)
    with ef1:
        pet_filter = st.selectbox("Filter by pet",
            ["All pets"] + [p.name for p in owner.pets], key="ef_pet")
    with ef2:
        status_filter = st.selectbox("Filter by status",
            ["All", "Pending", "Completed"], key="ef_status")
    with ef3:
        cat_filter = st.selectbox("Filter by category",
            ["All", "exercise", "feeding", "medical", "grooming", "general"],
            key="ef_cat")

    f_pet_name  = None if pet_filter   == "All pets"   else pet_filter
    f_completed = None if status_filter == "All"        else (status_filter == "Completed")
    f_category  = None if cat_filter   == "All"         else cat_filter

    filtered = owner.filter_tasks(
        completed=f_completed,
        pet_name=f_pet_name,
        category=f_category,
    )

    if filtered:
        # Apply sort_by_time so the preview matches what the scheduler will do
        sorted_filtered = Scheduler.sort_by_time(filtered)
        st.caption(
            f"Showing **{len(sorted_filtered)}** task(s) — "
            "sorted morning → afternoon → evening → no preference"
        )
        rows = []
        for t in sorted_filtered:
            freq_badge = {"daily": "🔁", "weekly": "📅", "as-needed": "🔔"}.get(t.frequency, "")
            rows.append({
                "Task":      t.title,
                "Min":       t.duration_minutes,
                "Priority":  t.priority,
                "Time pref": t.preferred_time or "—",
                "Pinned":    t.pinned_start or "—",
                "Freq":      freq_badge,
                "Done":      "✓" if t.completed else "○",
            })
        st.table(rows)
    else:
        st.info("No tasks match the selected filters.")
elif owner:
    st.info("Add tasks in Section 2 to explore them here.")
else:
    st.warning("Set up an owner first.")

st.divider()


# ============================================================================
# Section 4 – Generate schedule
# ============================================================================
st.subheader("4 · Generate today's schedule")

if owner is None:
    st.warning("Set up an owner first.")
elif not owner.pets:
    st.warning("Add at least one pet with tasks.")
elif owner.total_task_minutes() == 0:
    st.warning("Add at least one task to a pet before scheduling.")
else:
    total_mins = owner.total_task_minutes()
    avail      = owner.available_minutes
    ma, mb, mc = st.columns(3)
    ma.metric("Total task time",  f"{total_mins} min")
    mb.metric("Time available",   f"{avail} min")
    mc.metric("Slack / overflow", f"{avail - total_mins:+d} min",
              delta_color="normal" if avail >= total_mins else "inverse")

    if st.button("🗓  Generate schedule", type="primary"):
        st.session_state.schedule = Scheduler(owner=owner).generate_plan()

# ── Display plan ──────────────────────────────────────────────────────────────
plan = st.session_state.schedule
if plan is not None:
    st.divider()
    st.subheader("📋 Today's plan")

    # ── Conflict banner ───────────────────────────────────────────────────────
    if plan.conflicts:
        st.error(
            f"**⚠ {len(plan.conflicts)} scheduling conflict(s) detected** — "
            "two or more pinned tasks overlap. Review your pinned start times."
        )
        for warning in plan.conflicts:
            st.warning(warning)

    # ── Scheduled tasks ───────────────────────────────────────────────────────
    if not plan.entries:
        st.error("No tasks could be scheduled within the available time.")
    else:
        for entry in plan.entries:
            status_icon = "✅" if entry.task.completed else "🔲"
            pin_badge   = " 📌" if entry.task.pinned_start else ""
            freq_badge  = {"daily": " 🔁", "weekly": " 📅", "as-needed": " 🔔"}.get(
                entry.task.frequency, ""
            )

            with st.container(border=True):
                left, right = st.columns([5, 1])
                with left:
                    st.markdown(
                        f"**{status_icon}{pin_badge} {entry.task.title}**{freq_badge}  "
                        f"· {entry.start_time_str()} – {entry.end_time_str()}"
                    )
                    priority_colour = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                        entry.task.priority, ""
                    )
                    st.caption(
                        f"{priority_colour} {entry.task.priority} priority  |  "
                        f"{entry.task.duration_minutes} min  |  "
                        f"category: {entry.task.category}  |  "
                        f"↳ _{entry.reason}_"
                    )
                with right:
                    if not entry.task.completed:
                        if st.button("✓ Done", key=f"done_{id(entry.task)}"):
                            entry.task.mark_complete()
                            st.rerun()
                    else:
                        st.caption("Done!")

    # ── Skipped tasks ─────────────────────────────────────────────────────────
    if plan.skipped_tasks:
        with st.expander(
            f"⏭  {len(plan.skipped_tasks)} task(s) skipped — didn't fit in available time"
        ):
            for t in plan.skipped_tasks:
                st.write(
                    f"- **{t.title}** · {t.duration_minutes} min · "
                    f"{t.priority} priority · {t.category}"
                )
            st.caption(
                "Tip: increase your available time or remove lower-priority tasks "
                "to fit these into the schedule."
            )

    # ── Summary bar ───────────────────────────────────────────────────────────
    sa, sb, sc = st.columns(3)
    sa.metric("Scheduled",   f"{len(plan.entries)} tasks")
    sb.metric("Minutes used", f"{plan.total_scheduled_minutes()} / {owner.available_minutes}")
    sc.metric("Conflicts",    len(plan.conflicts),
              delta_color="off" if plan.conflicts == [] else "inverse")

    if not plan.conflicts:
        st.success("No scheduling conflicts — your day looks good! 🐾")
