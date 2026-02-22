import streamlit as st
from database import (
    CASE_STATUSES, STATUS_ICONS,
    add_project, get_all_projects, update_project, delete_project,
    assign_case_to_project, unassign_case_from_project,
    get_cases_for_project, get_all_cases,
    get_case_crime_types, get_primary_crime_type,
)

st.title("Projects")
st.caption("Group related cases into named investigation projects. Use the sidebar to filter all views to a single project.")

tab_manage, tab_assign, tab_summary = st.tabs([
    "Manage Projects", "Assign Cases", "Project Summary"
])

# ─────────────────────────────────────────────
# Tab 1 — Manage Projects
# ─────────────────────────────────────────────
with tab_manage:
    with st.form("new_project_form", clear_on_submit=True):
        st.subheader("New Project")
        col1, col2 = st.columns([1, 2])
        with col1:
            proj_name = st.text_input("Project Name")
        with col2:
            proj_desc = st.text_area("Description", height=68)
        if st.form_submit_button("Create Project"):
            if not proj_name.strip():
                st.error("Project name is required.")
            else:
                try:
                    add_project(proj_name.strip(), proj_desc.strip())
                    st.success(f"Project '{proj_name.strip()}' created.")
                    st.rerun()
                except Exception as e:
                    if "UNIQUE constraint" in str(e):
                        st.error("A project with that name already exists.")
                    else:
                        st.error(f"Error: {e}")

    st.divider()
    projects = get_all_projects()

    if not projects:
        st.info("No projects yet. Create one above.")
    else:
        st.subheader(f"All Projects ({len(projects)})")
        for p in projects:
            proj_cases = get_cases_for_project(p["id"])
            case_count = len(proj_cases)
            with st.expander(f"**{p['name']}**  ({case_count} case{'s' if case_count != 1 else ''})"):
                st.markdown(p["description"] or "_No description._")
                st.caption(f"Created: {p['created_at']}")

                # Inline edit
                if st.session_state.get(f"editing_proj_{p['id']}"):
                    with st.form(f"edit_proj_form_{p['id']}", clear_on_submit=False):
                        new_name = st.text_input("Name", value=p["name"])
                        new_desc = st.text_area("Description", value=p["description"] or "")
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.form_submit_button("Save"):
                                if new_name.strip():
                                    update_project(p["id"], name=new_name.strip(), description=new_desc.strip())
                                    st.session_state.pop(f"editing_proj_{p['id']}", None)
                                    st.rerun()
                        with col_cancel:
                            if st.form_submit_button("Cancel"):
                                st.session_state.pop(f"editing_proj_{p['id']}", None)
                                st.rerun()
                else:
                    btn1, btn2, _ = st.columns([1, 1, 4])
                    with btn1:
                        if st.button("Edit", key=f"edit_proj_{p['id']}"):
                            st.session_state[f"editing_proj_{p['id']}"] = True
                            st.rerun()
                    with btn2:
                        if st.button("Delete", key=f"del_proj_{p['id']}"):
                            delete_project(p["id"])
                            if st.session_state.get("active_project_id") == p["id"]:
                                st.session_state["active_project_id"] = None
                                st.session_state["active_project_name"] = "(All Cases)"
                            st.rerun()

# ─────────────────────────────────────────────
# Tab 2 — Assign Cases
# ─────────────────────────────────────────────
with tab_assign:
    projects = get_all_projects()
    if not projects:
        st.warning("Create a project first (Manage Projects tab).")
    else:
        proj_options = {p["name"]: p["id"] for p in projects}
        selected_proj_name = st.selectbox("Select Project", list(proj_options.keys()), key="assign_proj_sel")
        selected_proj_id = proj_options[selected_proj_name]

        all_cases = get_all_cases()
        proj_cases = get_cases_for_project(selected_proj_id)
        proj_case_ids = {c["id"] for c in proj_cases}

        if not all_cases:
            st.info("No cases exist yet. Add cases on the Cases page.")
        else:
            col_avail, col_assigned = st.columns(2)

            with col_avail:
                st.markdown("**Available Cases**")
                unassigned = [c for c in all_cases if c["id"] not in proj_case_ids]
                if not unassigned:
                    st.caption("All cases are already in this project.")
                for c in unassigned:
                    types_str = ", ".join(get_case_crime_types(c["id"])) or "Unknown"
                    label = f"#{c['id']} — {c['title']}"
                    bcol, lcol = st.columns([1, 4])
                    with bcol:
                        if st.button("Add →", key=f"add_{selected_proj_id}_{c['id']}"):
                            assign_case_to_project(selected_proj_id, c["id"])
                            st.rerun()
                    with lcol:
                        st.markdown(f"{label}")
                        st.caption(types_str)

            with col_assigned:
                st.markdown("**In This Project**")
                if not proj_cases:
                    st.caption("No cases assigned yet.")
                for c in proj_cases:
                    types_str = ", ".join(get_case_crime_types(c["id"])) or "Unknown"
                    label = f"#{c['id']} — {c['title']}"
                    bcol, lcol = st.columns([1, 4])
                    with bcol:
                        if st.button("← Remove", key=f"rem_{selected_proj_id}_{c['id']}"):
                            unassign_case_from_project(selected_proj_id, c["id"])
                            st.rerun()
                    with lcol:
                        st.markdown(f"{label}")
                        st.caption(types_str)

# ─────────────────────────────────────────────
# Tab 3 — Project Summary
# ─────────────────────────────────────────────
with tab_summary:
    projects = get_all_projects()
    if not projects:
        st.info("No projects to summarise.")
    else:
        for p in projects:
            proj_cases = get_cases_for_project(p["id"])
            st.subheader(p["name"])
            if p["description"]:
                st.caption(p["description"])

            total  = len(proj_cases)
            murders = sum(1 for c in proj_cases if c.get("is_murder"))
            active  = sum(1 for c in proj_cases if c["status"] == "Active")
            cold    = sum(1 for c in proj_cases if c["status"] == "Cold Case")
            solved  = sum(1 for c in proj_cases if c["status"] == "Solved")

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Total Cases",   total)
            m2.metric("🔴 Murders",    murders)
            m3.metric("🟢 Active",     active)
            m4.metric("🧊 Cold Case",  cold)
            m5.metric("✅ Solved",     solved)

            # Crime type breakdown
            all_types: dict[str, int] = {}
            for c in proj_cases:
                for ct in get_case_crime_types(c["id"]):
                    all_types[ct] = all_types.get(ct, 0) + 1
            if all_types:
                breakdown = ", ".join(
                    f"{ct} ({n})"
                    for ct, n in sorted(all_types.items(), key=lambda x: -x[1])
                )
                st.markdown(f"**Crime Types:** {breakdown}")

            with st.expander("View Cases", expanded=False):
                for c in proj_cases:
                    types_str = ", ".join(get_case_crime_types(c["id"])) or "Unknown"
                    icon = STATUS_ICONS.get(c["status"], "")
                    murder_tag = " 🔴" if c.get("is_murder") else ""
                    st.markdown(
                        f"- **#{c['id']}** {c['title']}{murder_tag} — {types_str} — {icon} {c['status']}"
                    )

            st.divider()
