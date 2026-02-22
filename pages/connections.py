import streamlit as st
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from database import (
    get_all_cases, link_cases, get_all_case_links, delete_case_link,
    get_case_crime_types,
)

st.title("Case Connections")

project_id   = st.session_state.get("active_project_id")
project_name = st.session_state.get("active_project_name", "All Cases")

cases = get_all_cases(project_id=project_id)

# ── Case label helper ──────────────────────────
def case_label(c: dict) -> str:
    types = get_case_crime_types(c["id"])
    types_str = ", ".join(types) if types else "Unknown"
    return f"#{c['id']} — {c['title']} ({types_str})"

# ── Link Two Cases ────────────────────────────
if len(cases) < 2:
    st.info("Add at least two cases to create connections." if not project_id
            else f"Project '{project_name}' needs at least two cases to create connections.")
else:
    with st.form("link_cases_form", clear_on_submit=True):
        st.subheader("Link Two Cases")
        case_options = {case_label(c): c["id"] for c in cases}
        option_keys  = list(case_options.keys())

        col1, col2 = st.columns(2)
        with col1:
            sel1 = st.selectbox("Case 1", option_keys, index=0)
        with col2:
            sel2 = st.selectbox("Case 2", option_keys, index=min(1, len(option_keys) - 1))

        similarity_note = st.text_input(
            "Similarity Note",
            placeholder="e.g. Same MO, Same area, Matching DNA, Identical ligature marks"
        )

        if st.form_submit_button("Create Link"):
            id1 = case_options[sel1]
            id2 = case_options[sel2]
            if id1 == id2:
                st.error("Cannot link a case to itself.")
            elif not similarity_note.strip():
                st.error("Similarity note is required.")
            else:
                try:
                    link_cases(id1, id2, similarity_note.strip())
                    st.success("Cases linked.")
                    st.rerun()
                except Exception as e:
                    if "UNIQUE constraint" in str(e) or "CHECK constraint" in str(e):
                        st.error("These cases are already linked.")
                    else:
                        st.error(f"Error: {e}")

# ── Existing Links Table ──────────────────────
st.divider()
links = get_all_case_links(project_id=project_id)

if not links:
    st.info("No case links yet." if not project_id else f"No case links in project '{project_name}'.")
else:
    st.subheader(f"Case Links ({len(links)}) — {project_name}")
    for lnk in links:
        col1, col2, col3 = st.columns([3, 3, 1])
        with col1:
            st.markdown(f"**#{lnk['case_id_1']}** {lnk['case1_title']}")
        with col2:
            st.markdown(f"**#{lnk['case_id_2']}** {lnk['case2_title']}")
        with col3:
            if st.button("Remove", key=f"del_cl_{lnk['id']}"):
                delete_case_link(lnk["id"])
                st.rerun()
        st.caption(f"Note: {lnk['similarity_note']}  |  Created: {lnk['created_at']}")
        st.divider()

# ── Network Graph ─────────────────────────────
st.subheader("Network Graph")

if not links:
    st.info("Link two cases above to see the network graph.")
else:
    G = nx.Graph()
    case_map = {c["id"]: c for c in get_all_cases(project_id=project_id)}

    linked_ids = set()
    for lnk in links:
        linked_ids.add(lnk["case_id_1"])
        linked_ids.add(lnk["case_id_2"])

    for cid in linked_ids:
        c = case_map.get(cid)
        if c:
            G.add_node(cid, label=f"#{cid}\n{c['title'][:22]}")

    for lnk in links:
        G.add_edge(lnk["case_id_1"], lnk["case_id_2"], label=lnk["similarity_note"])

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#0e1117")

    pos = nx.spring_layout(G, seed=42, k=2.0)

    nx.draw_networkx_nodes(G, pos, ax=ax, node_color="#4a9eff", node_size=900,
                           edgecolors="#ffffff", linewidths=1.5)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#ff4444", width=2, style="dashed")
    nx.draw_networkx_labels(G, pos, ax=ax,
                            labels=nx.get_node_attributes(G, "label"),
                            font_color="white", font_size=8, font_weight="bold")
    nx.draw_networkx_edge_labels(G, pos, ax=ax,
                                 edge_labels=nx.get_edge_attributes(G, "label"),
                                 font_color="#ffaaaa", font_size=7)
    ax.set_axis_off()
    st.pyplot(fig)
    plt.close(fig)
