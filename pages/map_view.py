import streamlit as st
import folium
from streamlit_folium import st_folium
from database import (
    CRIME_TYPES, CASE_STATUSES, STATUS_ICONS,
    get_cases_with_coordinates, get_linked_pairs_with_coordinates,
    get_case_tags,
)

st.title("Crime Map")

CRIME_TYPE_COLORS = {
    "Homicide":             "red",
    "Assault":              "orange",
    "Sexual Assault":       "purple",
    "Robbery":              "darkred",
    "Burglary":             "blue",
    "Theft":                "lightblue",
    "Motor Vehicle Theft":  "cadetblue",
    "Arson":                "darkred",
    "Fraud":                "green",
    "Forgery":              "lightgreen",
    "Drug Offense":         "darkgreen",
    "Kidnapping":           "pink",
    "Domestic Violence":    "cadetblue",
    "Human Trafficking":    "darkpurple",
    "Cybercrime":           "lightgreen",
    "Vandalism":            "gray",
    "Weapons Offense":      "orange",
    "Gang Activity":        "darkred",
    "Missing Person":       "pink",
    "Other":                "beige",
}

ICON_HEX = {
    "red": "#d63e2a", "orange": "#f69730", "purple": "#9b59b6",
    "darkred": "#a23336", "blue": "#38aadd", "lightblue": "#8adaff",
    "cadetblue": "#436978", "green": "#72b026", "lightgreen": "#bbf970",
    "darkgreen": "#728224", "pink": "#ff91ea", "darkpurple": "#5b3566",
    "gray": "#575757", "lightgray": "#a3a3a3", "beige": "#ffcb92",
}

# ── Filters ──────────────────────────────────
project_id   = st.session_state.get("active_project_id")
project_name = st.session_state.get("active_project_name", "All Cases")

filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    selected_types = st.multiselect("Crime Types", CRIME_TYPES, default=CRIME_TYPES)
with filter_col2:
    selected_statuses = st.multiselect("Status", CASE_STATUSES, default=CASE_STATUSES)

# ── Data ─────────────────────────────────────
all_cases = get_cases_with_coordinates(project_id=project_id)
cases = [
    c for c in all_cases
    if c["status"] in selected_statuses
    and (c.get("primary_crime_type") in selected_types or not c.get("primary_crime_type"))
]
linked_pairs = get_linked_pairs_with_coordinates(project_id=project_id)

# ── Map ──────────────────────────────────────
if cases:
    lats = [c["crime_scene_lat"] for c in cases if c.get("crime_scene_lat")]
    lons = [c["crime_scene_lon"] for c in cases if c.get("crime_scene_lon")]
    avg_lat = sum(lats) / len(lats) if lats else 54.0
    avg_lon = sum(lons) / len(lons) if lons else 15.0
else:
    avg_lat, avg_lon = 54.0, 15.0

m = folium.Map(location=[avg_lat, avg_lon], zoom_start=6, tiles="CartoDB dark_matter")

for c in cases:
    color = CRIME_TYPE_COLORS.get(c.get("primary_crime_type"), "beige")
    vc_str = f" ({c['victim_count']} victim{'s' if (c.get('victim_count') or 1) > 1 else ''})" if c.get("is_murder") else ""
    murder_badge = f"<span style='color:#ff4444;font-weight:bold;'>🔴 MURDER{vc_str}</span><br>" if c.get("is_murder") else ""
    scene_addr = c.get("crime_scene_address") or "N/A"
    body_addr  = c.get("body_found_address")  or "—"
    mo_snippet = (c.get("mo_description") or "")[:120]
    status_icon = STATUS_ICONS.get(c["status"], "")

    popup_html = f"""
    <div style="font-family:sans-serif; color:#e0e0e0; background:#1a1f2e;
                padding:10px; border-radius:6px; min-width:230px; max-width:320px;">
        <h4 style="margin:0 0 6px 0; color:#4a9eff;">#{c['id']} {c['title']}</h4>
        {murder_badge}
        <p style="margin:2px 0;"><b>Type:</b> {c.get('primary_crime_type','N/A')}</p>
        <p style="margin:2px 0;"><b>Date:</b> {c['date_occurred']}</p>
        <p style="margin:2px 0;"><b>Status:</b> {status_icon} {c['status']}</p>
        <p style="margin:2px 0;"><b>📍 Crime Scene:</b> {scene_addr}</p>
        <p style="margin:2px 0;"><b>🏚️ Body Found:</b> {body_addr}</p>
        {'<p style="margin:2px 0;"><b>MO:</b> ' + mo_snippet + '</p>' if mo_snippet else ''}
    </div>
    """

    # Crime scene marker (solid)
    folium.Marker(
        location=[c["crime_scene_lat"], c["crime_scene_lon"]],
        popup=folium.Popup(popup_html, max_width=340),
        tooltip=f"#{c['id']} {c['title']} [Scene]",
        icon=folium.Icon(color=color, icon="info-sign"),
    ).add_to(m)

    # Body found marker + connector line (if different location set)
    if c.get("body_found_lat") and c.get("body_found_lon"):
        folium.Marker(
            location=[c["body_found_lat"], c["body_found_lon"]],
            popup=folium.Popup(popup_html.replace("📍 Crime Scene", "🏚️ Body Found"), max_width=340),
            tooltip=f"#{c['id']} {c['title']} [Body Found]",
            icon=folium.Icon(color=color, icon="home", prefix="fa"),
        ).add_to(m)

        # Thin yellow dashed line scene → body
        folium.PolyLine(
            locations=[
                [c["crime_scene_lat"], c["crime_scene_lon"]],
                [c["body_found_lat"],  c["body_found_lon"]],
            ],
            color="#ffcc00",
            weight=1.5,
            dash_array="6",
            tooltip=f"#{c['id']} Scene → Body distance",
        ).add_to(m)

# Red dashed lines between linked cases
for pair in linked_pairs:
    folium.PolyLine(
        locations=[
            [pair["c1_lat"], pair["c1_lon"]],
            [pair["c2_lat"], pair["c2_lon"]],
        ],
        color="#ff4444",
        weight=2,
        dash_array="10",
        tooltip=f"Case link: {pair['similarity_note']}",
    ).add_to(m)

# Legend
legend_html = """
<div style="position:fixed; bottom:30px; right:30px; z-index:9999;
            background:#1a1f2e; border:1px solid #1e2a3a; border-radius:8px;
            padding:10px 14px; font-family:sans-serif; font-size:12px; color:#e0e0e0;
            max-height:320px; overflow-y:auto; min-width:180px;">
<b style="font-size:13px;">Legend</b><br>
"""
for crime, cname in CRIME_TYPE_COLORS.items():
    hex_c = ICON_HEX.get(cname, "#ffffff")
    legend_html += f'<span style="color:{hex_c};">&#9679;</span> {crime}<br>'
legend_html += '<hr style="border-color:#1e2a3a; margin:4px 0;">'
legend_html += '<span style="color:#ff4444;">- - -</span> Linked Cases<br>'
legend_html += '<span style="color:#ffcc00;">- - -</span> Scene → Body Found<br>'
legend_html += "</div>"

m.get_root().html.add_child(folium.Element(legend_html))

st_folium(m, width=None, height=640, returned_objects=[])
st.caption(f"Showing {len(cases)} case location(s) · {project_name}")
