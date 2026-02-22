import streamlit as st
from datetime import date as date_cls
from database import (
    CRIME_TYPES, CONNECTION_TYPES, CONVICTION_STATUSES,
    add_suspect, get_all_suspects, update_suspect, delete_suspect,
    get_all_cases, link_suspect_to_case, get_cases_for_suspect,
    delete_suspect_case_link,
    add_suspect_crime_history, get_suspect_crime_history,
    delete_suspect_crime_history_entry,
    get_case_crime_types,
)

st.title("Suspects")

CONVICTION_ICONS = {
    "Convicted": "🔴",
    "Arrested":  "🟡",
    "Suspected": "⚪",
}


def parse_date_parts(date_str):
    if date_str:
        try:
            d = date_cls.fromisoformat(date_str)
            return d.year, d.month, d.day
        except ValueError:
            pass
    return 2000, 1, 1


tab_list, tab_link = st.tabs(["Manage Suspects", "Link Suspect to Case"])

# ─────────────────────────────────────────────
# Tab 1 — Manage Suspects
# ─────────────────────────────────────────────
with tab_list:
    with st.form("add_suspect_form", clear_on_submit=True):
        st.subheader("Add New Suspect")
        col1, col2 = st.columns(2)
        with col1:
            name    = st.text_input("Name")
            aliases = st.text_input("Known Aliases (comma-separated)")
        with col2:
            description = st.text_area("Description", height=100)

        if st.form_submit_button("Add Suspect"):
            if not name.strip():
                st.error("Name is required.")
            else:
                add_suspect(name.strip(), description.strip(), aliases.strip())
                st.success(f"Suspect '{name.strip()}' added.")
                st.rerun()

    st.divider()
    suspects = get_all_suspects()

    if not suspects:
        st.info("No suspects yet.")
    else:
        st.subheader(f"All Suspects ({len(suspects)})")
        for s in suspects:
            alias_str = f"  (aka {s['known_aliases']})" if s["known_aliases"] else ""
            with st.expander(f"{s['name']}{alias_str}"):

                # Basic info
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Description:** {s['description'] or 'N/A'}")
                with col2:
                    st.markdown(f"**Aliases:** {s['known_aliases'] or 'None'}")

                # ── Linked Cases ──────────────────────
                st.divider()
                st.markdown("**🔗 Linked Cases**")
                linked = get_cases_for_suspect(s["id"])
                if linked:
                    for lnk in linked:
                        types_str = lnk.get("crime_types") or "Unknown"
                        lc1, lc2 = st.columns([5, 1])
                        with lc1:
                            st.markdown(
                                f"- #{lnk['case_id']} **{lnk['case_title']}** "
                                f"({types_str}) — _{lnk['connection_type']}_"
                            )
                        with lc2:
                            if st.button("Unlink", key=f"unlink_sc_{lnk['id']}"):
                                delete_suspect_case_link(lnk["id"])
                                st.rerun()
                else:
                    st.caption("Not linked to any cases.")

                # ── Criminal History ──────────────────
                st.divider()
                st.markdown("**📋 Criminal History / Prior Record**")

                history = get_suspect_crime_history(s["id"])
                if history:
                    for entry in history:
                        hc1, hc2, hc3, hc4 = st.columns([2, 2, 2, 1])
                        with hc1:
                            st.markdown(f"**{entry['crime_type']}**")
                        with hc2:
                            st.caption(entry["date_of_crime"] or "Date unknown")
                        with hc3:
                            badge = CONVICTION_ICONS.get(entry["conviction_status"], "")
                            st.markdown(f"{badge} {entry['conviction_status']}")
                        with hc4:
                            if st.button("Remove", key=f"del_hist_{entry['id']}"):
                                delete_suspect_crime_history_entry(entry["id"])
                                st.rerun()
                        if entry.get("notes"):
                            st.caption(f"  Notes: {entry['notes']}")
                else:
                    st.caption("No prior record entries.")

                # Add history entry form
                with st.expander("+ Add Criminal History Entry", expanded=False):
                    with st.form(f"hist_form_{s['id']}", clear_on_submit=True):
                        hcol1, hcol2, hcol3 = st.columns(3)
                        with hcol1:
                            h_crime = st.selectbox("Crime Type", CRIME_TYPES,
                                                   key=f"hct_{s['id']}")
                        with hcol2:
                            h_conv = st.selectbox("Conviction Status", CONVICTION_STATUSES,
                                                  key=f"hconv_{s['id']}")
                        with hcol3:
                            h_unknown = st.checkbox("Date unknown", value=True,
                                                    key=f"hunk_{s['id']}")

                        h_date_str = None
                        if not h_unknown:
                            st.markdown("**Date of Crime**")
                            hy_col, hm_col, hd_col = st.columns(3)
                            with hy_col:
                                hy = st.number_input("Year",  min_value=1800,
                                                     max_value=date_cls.today().year,
                                                     value=2000, step=1, key=f"hy_{s['id']}")
                            with hm_col:
                                hm = st.number_input("Month", min_value=1, max_value=12,
                                                     value=1, step=1, key=f"hm_{s['id']}")
                            with hd_col:
                                hd = st.number_input("Day",   min_value=1, max_value=31,
                                                     value=1, step=1, key=f"hd_{s['id']}")

                        h_notes = st.text_area("Notes", height=60, key=f"hnotes_{s['id']}")

                        if st.form_submit_button("Add Entry"):
                            if not h_unknown:
                                try:
                                    h_date_str = str(date_cls(int(hy), int(hm), int(hd)))
                                except ValueError:
                                    st.error("Invalid date — check month/day values.")
                                    st.stop()
                            add_suspect_crime_history(
                                suspect_id=s["id"],
                                crime_type=h_crime,
                                date_of_crime=h_date_str,
                                conviction_status=h_conv,
                                notes=h_notes.strip(),
                            )
                            st.success("History entry added.")
                            st.rerun()

                # Delete suspect
                st.divider()
                _, del_col, _ = st.columns([3, 1, 3])
                with del_col:
                    if st.button("🗑️ Delete Suspect", key=f"del_s_{s['id']}"):
                        delete_suspect(s["id"])
                        st.rerun()

# ─────────────────────────────────────────────
# Tab 2 — Link Suspect to Case
# ─────────────────────────────────────────────
with tab_link:
    suspects = get_all_suspects()
    cases    = get_all_cases()

    if not suspects:
        st.warning("Add at least one suspect first.")
    elif not cases:
        st.warning("Add at least one case first.")
    else:
        with st.form("link_suspect_form", clear_on_submit=True):
            st.subheader("Link Suspect to Case")

            susp_opts = {f"{s['name']} (ID: {s['id']})": s["id"] for s in suspects}
            sel_susp  = st.selectbox("Suspect", list(susp_opts.keys()))

            # Build case labels with primary crime type
            case_opts = {}
            for c in cases:
                primary = get_case_crime_types(c["id"])
                types_str = ", ".join(primary) if primary else "Unknown"
                case_opts[f"#{c['id']} — {c['title']} ({types_str})"] = c["id"]
            sel_case = st.selectbox("Case", list(case_opts.keys()))

            conn_type = st.selectbox("Connection Type", CONNECTION_TYPES)
            notes     = st.text_area("Notes", height=80)

            if st.form_submit_button("Create Link"):
                sid = susp_opts[sel_susp]
                cid = case_opts[sel_case]
                try:
                    link_suspect_to_case(sid, cid, conn_type, notes.strip())
                    st.success("Suspect linked to case.")
                    st.rerun()
                except Exception as e:
                    if "UNIQUE constraint" in str(e):
                        st.error("This suspect is already linked to this case with that connection type.")
                    else:
                        st.error(f"Error: {e}")
