import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import date as date_cls
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from database import (
    CRIME_TYPES, CASE_STATUSES, CASE_TAGS, STATUS_ICONS,
    add_case, get_all_cases, get_case, update_case, delete_case,
    set_case_crime_types, get_case_crime_types,
    set_case_tags, get_case_tags,
)

st.title("Cases")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def geocode_address(address: str):
    """Returns (lat, lon) or None."""
    try:
        geo = Nominatim(user_agent="cold_case_tool_v1", timeout=6)
        loc = geo.geocode(address)
        if loc:
            return loc.latitude, loc.longitude
    except (GeocoderTimedOut, GeocoderServiceError):
        pass
    return None


def parse_date_parts(date_str: str | None):
    """Parse 'YYYY-MM-DD' into (year, month, day) ints. Defaults to (2000,1,1)."""
    if date_str:
        try:
            d = date_cls.fromisoformat(date_str)
            return d.year, d.month, d.day
        except ValueError:
            pass
    return 2000, 1, 1


def date_inputs(label_prefix: str, default_y=2000, default_m=1, default_d=1, key_prefix=""):
    """Render Year/Month/Day number inputs and return (year, month, day)."""
    st.markdown(f"**{label_prefix}**")
    c1, c2, c3 = st.columns(3)
    with c1:
        y = st.number_input("Year",  min_value=1800, max_value=date_cls.today().year,
                             value=default_y, step=1, key=f"{key_prefix}_y")
    with c2:
        m = st.number_input("Month", min_value=1, max_value=12,
                             value=default_m, step=1, key=f"{key_prefix}_m")
    with c3:
        d = st.number_input("Day",   min_value=1, max_value=31,
                             value=default_d, step=1, key=f"{key_prefix}_d")
    return int(y), int(m), int(d)


def location_picker(section: str, key: str, default_lat=54.0, default_lon=15.0):
    """
    Renders address input + geocode button + interactive map picker.
    Stores result in session_state[key+'_lat'] and session_state[key+'_lon'].
    Also renders address text in session_state[key+'_addr'].
    Returns nothing — caller reads session state.
    """
    addr_key  = key + "_addr"
    lat_key   = key + "_lat"
    lon_key   = key + "_lon"

    addr = st.text_input(f"Address / Description — {section}", key=addr_key)
    col_btn, col_coords = st.columns([1, 3])

    with col_btn:
        if st.button(f"📍 Find Coordinates", key=key + "_geocode"):
            if addr.strip():
                with st.spinner("Searching…"):
                    result = geocode_address(addr.strip())
                if result:
                    st.session_state[lat_key] = result[0]
                    st.session_state[lon_key] = result[1]
                    st.rerun()
                else:
                    st.warning("Address not found. Try a more specific address or click on the map below.")
            else:
                st.warning("Enter an address first.")

    with col_coords:
        lat_val = st.session_state.get(lat_key)
        lon_val = st.session_state.get(lon_key)
        if lat_val and lon_val:
            st.success(f"📍 {lat_val:.5f}, {lon_val:.5f}")
            if st.button("Clear", key=key + "_clear"):
                st.session_state[lat_key] = None
                st.session_state[lon_key] = None
                st.rerun()
        else:
            st.caption("No coordinates set — use address search or click the map.")

    # Interactive map picker
    with st.expander(f"📌 Click map to pin {section} location", expanded=False):
        map_lat = st.session_state.get(lat_key) or default_lat
        map_lon = st.session_state.get(lon_key) or default_lon
        m = folium.Map(location=[map_lat, map_lon], zoom_start=5 if not st.session_state.get(lat_key) else 12,
                       tiles="CartoDB dark_matter")
        if st.session_state.get(lat_key):
            folium.Marker(
                [st.session_state[lat_key], st.session_state[lon_key]],
                icon=folium.Icon(color="red", icon="crosshairs"),
            ).add_to(m)
        clicked = st_folium(m, height=280, returned_objects=["last_clicked"], key=key + "_map")
        if clicked and clicked.get("last_clicked"):
            st.session_state[lat_key] = clicked["last_clicked"]["lat"]
            st.session_state[lon_key] = clicked["last_clicked"]["lng"]
            st.rerun()


def init_location_state(prefix: str, case: dict | None):
    """Pre-fill session state from existing case on first edit load."""
    if case and st.session_state.get("_loc_loaded") != case["id"]:
        for suffix, col in [("_lat", "crime_scene_lat"), ("_lon", "crime_scene_lon"),
                             ("_addr", "crime_scene_address")]:
            st.session_state[f"cs{suffix}"] = case.get(col)
        for suffix, col in [("_lat", "body_found_lat"), ("_lon", "body_found_lon"),
                             ("_addr", "body_found_address")]:
            st.session_state[f"bf{suffix}"] = case.get(col)
        st.session_state["_loc_loaded"] = case["id"]
    elif not case:
        for k in ["cs_lat", "cs_lon", "cs_addr", "bf_lat", "bf_lon", "bf_addr"]:
            if k not in st.session_state:
                st.session_state[k] = None
        st.session_state.pop("_loc_loaded", None)


# ─────────────────────────────────────────────
# Add / Edit form
# ─────────────────────────────────────────────

editing_id   = st.session_state.get("editing_case_id")
editing_case = get_case(editing_id) if editing_id else None
show_form    = editing_case or st.session_state.get("show_case_form")

col_btn_new, _ = st.columns([1, 5])
with col_btn_new:
    if st.button("+ New Case" if not show_form else "Cancel"):
        if show_form:
            st.session_state.pop("editing_case_id", None)
            st.session_state.pop("show_case_form", None)
            st.session_state.pop("_loc_loaded", None)
        else:
            st.session_state["show_case_form"] = True
        st.rerun()

if show_form:
    init_location_state("cs", editing_case)

    st.subheader("Edit Case" if editing_case else "New Case")

    # ── Basic fields ──
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Title", value=editing_case["title"] if editing_case else "")
        status_idx = CASE_STATUSES.index(editing_case["status"]) if editing_case and editing_case["status"] in CASE_STATUSES else 0
        status = st.selectbox("Status", CASE_STATUSES, index=status_idx)

    with col2:
        existing_types = get_case_crime_types(editing_id) if editing_id else []
        crime_types = st.multiselect("Crime Type(s)", CRIME_TYPES, default=existing_types)

        existing_tags = get_case_tags(editing_id) if editing_id else []
        tags = st.multiselect("Tags", CASE_TAGS, default=existing_tags)

    # ── Date (historical-safe) ──
    st.divider()
    ey, em, ed = parse_date_parts(editing_case["date_occurred"] if editing_case else None)
    dy, dm, dd = date_inputs("Date Occurred", ey, em, ed, key_prefix="date_occ")

    # ── Murder section ──
    st.divider()
    is_murder = st.checkbox(
        "🔴 Murder Case",
        value=bool(editing_case["is_murder"]) if editing_case else False,
    )
    victim_count = None
    if is_murder:
        victim_count = st.number_input(
            "Number of Murder Victims",
            min_value=1, step=1,
            value=int(editing_case["victim_count"] or 1) if editing_case and editing_case.get("victim_count") else 1,
        )

    # ── MO + Victim profile ──
    st.divider()
    mo_desc  = st.text_area("MO Description",  value=editing_case["mo_description"]  or "" if editing_case else "")
    victim_p = st.text_area("Victim Profile",  value=editing_case["victim_profile"]  or "" if editing_case else "")

    # ── Crime Scene Location ──
    st.divider()
    st.subheader("📍 Crime Scene Location")
    location_picker("Crime Scene", "cs", default_lat=54.0, default_lon=15.0)

    # ── Body Found Location ──
    st.divider()
    st.subheader("🏚️ Body Found Location")
    location_picker("Body Found", "bf", default_lat=54.0, default_lon=15.0)

    # ── Save ──
    st.divider()
    if st.button("💾 Update Case" if editing_case else "💾 Save Case", type="primary"):
        # Validate
        errors = []
        if not title.strip():
            errors.append("Title is required.")
        if not crime_types:
            errors.append("At least one crime type is required.")
        try:
            date_val = date_cls(dy, dm, dd)
            date_str = str(date_val)
        except ValueError:
            errors.append(f"Invalid date: {dy}-{dm:02d}-{dd:02d}. Check month/day values.")
            date_str = None

        if errors:
            for e in errors:
                st.error(e)
        else:
            kwargs = dict(
                title=title.strip(),
                date_occurred=date_str,
                status=status,
                mo_description=mo_desc.strip(),
                victim_profile=victim_p.strip(),
                is_murder=is_murder,
                victim_count=int(victim_count) if is_murder and victim_count else None,
                crime_scene_address=st.session_state.get("cs_addr") or "",
                crime_scene_lat=st.session_state.get("cs_lat"),
                crime_scene_lon=st.session_state.get("cs_lon"),
                body_found_address=st.session_state.get("bf_addr") or "",
                body_found_lat=st.session_state.get("bf_lat"),
                body_found_lon=st.session_state.get("bf_lon"),
            )
            if editing_case:
                update_case(editing_id, **kwargs)
                set_case_crime_types(editing_id, crime_types)
                set_case_tags(editing_id, tags)
                st.session_state.pop("editing_case_id", None)
                st.success("Case updated.")
            else:
                new_id = add_case(**kwargs)
                set_case_crime_types(new_id, crime_types)
                set_case_tags(new_id, tags)
                st.success("Case added.")
            # Clear state
            for k in ["show_case_form", "_loc_loaded", "cs_lat", "cs_lon", "cs_addr",
                       "bf_lat", "bf_lon", "bf_addr"]:
                st.session_state.pop(k, None)
            st.rerun()

# ─────────────────────────────────────────────
# Case List
# ─────────────────────────────────────────────
st.divider()

project_id   = st.session_state.get("active_project_id")
project_name = st.session_state.get("active_project_name", "All Cases")
cases = get_all_cases(project_id=project_id)

filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    filter_status = st.multiselect("Filter by status", CASE_STATUSES, default=CASE_STATUSES)
with filter_col2:
    filter_types = st.multiselect("Filter by crime type", CRIME_TYPES, default=[])

filtered = [c for c in cases if c["status"] in filter_status]

if not filtered:
    st.info("No cases found. Adjust filters or add a new case.")
else:
    # Preload crime types for all cases (avoid N+1 in the loop display)
    ctypes_map = {c["id"]: get_case_crime_types(c["id"]) for c in filtered}
    tags_map   = {c["id"]: get_case_tags(c["id"])        for c in filtered}

    if filter_types:
        filtered = [c for c in filtered if any(t in filter_types for t in ctypes_map[c["id"]])]

    st.subheader(f"Cases — {project_name} ({len(filtered)})")

    for c in filtered:
        types_str  = ", ".join(ctypes_map[c["id"]]) or "Unknown"
        icon       = STATUS_ICONS.get(c["status"], "")
        murder_tag = " 🔴" if c.get("is_murder") else ""
        header     = f"#{c['id']} — {c['title']}{murder_tag}  |  {types_str}  |  {icon} {c['status']}"

        with st.expander(header):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Date:** {c['date_occurred']}")
                st.markdown(f"**Status:** {icon} {c['status']}")
                if c.get("is_murder"):
                    vc = c.get("victim_count") or 1
                    st.markdown(f"**🔴 Murder** — {vc} victim{'s' if vc != 1 else ''}")
            with col2:
                st.markdown(f"**Crime Type(s):** {types_str}")
                if tags_map[c["id"]]:
                    st.markdown("**Tags:** " + "  ".join(f"`{t}`" for t in tags_map[c["id"]]))

            # Locations
            loc_col1, loc_col2 = st.columns(2)
            with loc_col1:
                if c.get("crime_scene_address") or c.get("crime_scene_lat"):
                    st.markdown("**📍 Crime Scene**")
                    if c.get("crime_scene_address"):
                        st.markdown(c["crime_scene_address"])
                    if c.get("crime_scene_lat"):
                        st.caption(f"{c['crime_scene_lat']:.5f}, {c['crime_scene_lon']:.5f}")
            with loc_col2:
                if c.get("body_found_address") or c.get("body_found_lat"):
                    st.markdown("**🏚️ Body Found**")
                    if c.get("body_found_address"):
                        st.markdown(c["body_found_address"])
                    if c.get("body_found_lat"):
                        st.caption(f"{c['body_found_lat']:.5f}, {c['body_found_lon']:.5f}")

            if c.get("mo_description"):
                st.markdown(f"**MO:** {c['mo_description']}")
            if c.get("victim_profile"):
                st.markdown(f"**Victim Profile:** {c['victim_profile']}")

            st.caption(f"Created: {c['created_at']}")

            btn1, btn2, _ = st.columns([1, 1, 4])
            with btn1:
                if st.button("Edit", key=f"edit_{c['id']}"):
                    st.session_state["editing_case_id"] = c["id"]
                    st.session_state.pop("show_case_form", None)
                    st.session_state.pop("_loc_loaded", None)
                    st.rerun()
            with btn2:
                if st.button("Delete", key=f"del_{c['id']}"):
                    delete_case(c["id"])
                    st.rerun()
