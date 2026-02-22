import streamlit as st
from database import init_db, migrate_db, get_all_projects

st.set_page_config(
    page_title="Cold Case Management",
    page_icon="\U0001f6e1",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme CSS
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background-color: #0a0e14;
        border-right: 1px solid #1e2a3a;
    }
    .stApp header { background-color: #0a0e14; }
    [data-testid="stForm"] {
        border: 1px solid #1e2a3a;
        border-radius: 8px;
        padding: 1rem;
    }
    [data-testid="stMetric"] {
        background-color: #1a1f2e;
        border: 1px solid #1e2a3a;
        border-radius: 8px;
        padding: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

init_db()
migrate_db()

# ---- Global project filter in sidebar ----
with st.sidebar:
    st.divider()
    st.markdown("**🗂️ Active Project**")
    projects = get_all_projects()
    project_options = {"(All Cases)": None}
    project_options.update({p["name"]: p["id"] for p in projects})

    prior_id = st.session_state.get("active_project_id")
    prior_label = next(
        (label for label, pid in project_options.items() if pid == prior_id),
        "(All Cases)",
    )
    selected_label = st.selectbox(
        "Filter by project",
        list(project_options.keys()),
        index=list(project_options.keys()).index(prior_label),
        key="project_selector",
        label_visibility="collapsed",
    )
    st.session_state["active_project_id"] = project_options[selected_label]
    st.session_state["active_project_name"] = selected_label

pages = {
    "Investigation": [
        st.Page("pages/map_view.py",    title="Map",         icon=":material/map:"),
        st.Page("pages/cases.py",       title="Cases",       icon=":material/folder_open:"),
        st.Page("pages/suspects.py",    title="Suspects",    icon=":material/person_search:"),
        st.Page("pages/connections.py", title="Connections", icon=":material/hub:"),
        st.Page("pages/timeline.py",    title="Timeline",    icon=":material/timeline:"),
    ],
    "Organisation": [
        st.Page("pages/projects.py", title="Projects", icon=":material/work:"),
    ],
}

pg = st.navigation(pages, position="sidebar")
pg.run()
