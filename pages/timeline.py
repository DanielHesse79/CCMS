import streamlit as st
from datetime import date as date_cls
from database import (
    get_all_cases, add_timeline_event, get_timeline_events, delete_timeline_event,
    get_case_crime_types, STATUS_ICONS,
)

st.title("Timeline")

project_id   = st.session_state.get("active_project_id")
project_name = st.session_state.get("active_project_name", "All Cases")

cases = get_all_cases(project_id=project_id)

if not cases:
    st.info("Add at least one case to use the timeline." if not project_id
            else f"No cases in project '{project_name}' yet.")
else:
    # ── Case selector ──────────────────────────
    def case_label(c):
        types = get_case_crime_types(c["id"])
        types_str = ", ".join(types) if types else "Unknown"
        icon = STATUS_ICONS.get(c["status"], "")
        return f"#{c['id']} — {c['title']} ({types_str}) {icon}"

    case_options = {case_label(c): c["id"] for c in cases}
    selected_label   = st.selectbox("Select Case", list(case_options.keys()))
    selected_case_id = case_options[selected_label]

    # ── Add Event form ─────────────────────────
    with st.form("add_event_form", clear_on_submit=True):
        st.subheader("Add Timeline Event")

        col1, col2 = st.columns(2)
        with col1:
            event_title = st.text_input("Event Title")
            # Historical-safe date entry
            st.markdown("**Date**")
            dy_col, dm_col, dd_col = st.columns(3)
            with dy_col:
                ev_y = st.number_input("Year",  min_value=1800,
                                       max_value=date_cls.today().year,
                                       value=date_cls.today().year, step=1, key="ev_y")
            with dm_col:
                ev_m = st.number_input("Month", min_value=1, max_value=12,
                                       value=date_cls.today().month, step=1, key="ev_m")
            with dd_col:
                ev_d = st.number_input("Day",   min_value=1, max_value=31,
                                       value=date_cls.today().day,   step=1, key="ev_d")
        with col2:
            # Hour / minute
            st.markdown("**Time**")
            th_col, tm_col = st.columns(2)
            with th_col:
                ev_h  = st.number_input("Hour",   min_value=0, max_value=23, value=12, step=1)
            with tm_col:
                ev_min = st.number_input("Minute", min_value=0, max_value=59, value=0,  step=1)

        event_desc = st.text_area("Description / Lead / Note", height=80)

        if st.form_submit_button("Add Event"):
            if not event_title.strip():
                st.error("Event title is required.")
            else:
                try:
                    date_obj  = date_cls(int(ev_y), int(ev_m), int(ev_d))
                    timestamp = f"{date_obj} {int(ev_h):02d}:{int(ev_min):02d}"
                    add_timeline_event(selected_case_id, timestamp,
                                       event_title.strip(), event_desc.strip())
                    st.success("Event added.")
                    st.rerun()
                except ValueError:
                    st.error("Invalid date — check month/day values.")

    # ── Event list ─────────────────────────────
    st.divider()
    events = get_timeline_events(selected_case_id)

    if not events:
        st.info("No timeline events for this case yet.")
    else:
        st.subheader(f"Events ({len(events)})")
        for evt in events:
            with st.container(border=True):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"**{evt['title']}**")
                    st.caption(f"🕒 {evt['event_timestamp']}")
                with col2:
                    if st.button("Delete", key=f"del_evt_{evt['id']}"):
                        delete_timeline_event(evt["id"])
                        st.rerun()
                if evt.get("description"):
                    st.write(evt["description"])
