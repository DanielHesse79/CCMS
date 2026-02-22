import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases.db")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CRIME_TYPES = [
    "Homicide",
    "Assault",
    "Sexual Assault",
    "Robbery",
    "Burglary",
    "Theft",
    "Motor Vehicle Theft",
    "Arson",
    "Fraud",
    "Forgery",
    "Drug Offense",
    "Kidnapping",
    "Domestic Violence",
    "Human Trafficking",
    "Cybercrime",
    "Vandalism",
    "Weapons Offense",
    "Gang Activity",
    "Missing Person",
    "Other",
]

CONNECTION_TYPES = [
    "DNA Evidence",
    "Fingerprint Match",
    "Eyewitness Identification",
    "Phone Records / Cell Data",
    "CCTV / Video Evidence",
    "Financial Records",
    "Digital / Cyber Evidence",
    "Vehicle Link",
    "Ballistics Match",
    "Informant Tip",
    "Confession",
    "Physical Evidence",
    "Geographic Proximity",
    "Known Associate",
    "Prior Record",
    "Social Media Link",
    "Other",
]

CASE_STATUSES = ["Active", "Cold Case", "Solved"]

CONVICTION_STATUSES = ["Convicted", "Arrested", "Suspected"]

CASE_TAGS = [
    # Victim
    "Minor Victim",
    "Adult Victim",
    "Elderly Victim",
    "Multiple Victims",
    # Circumstances
    "Domestic",
    "Organized Crime",
    "Hate Crime",
    "Sexually Motivated",
    "Financially Motivated",
    "Random / Stranger",
    # Scene type
    "Indoor",
    "Outdoor",
    "Public Space",
    "Residential",
    "Wilderness / Rural",
    # Evidence
    "Weapon Recovered",
    "Forensic Evidence",
    "No Physical Evidence",
]

STATUS_ICONS = {
    "Active":    "🟢",
    "Cold Case": "🧊",
    "Solved":    "✅",
}


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# Schema init
# ---------------------------------------------------------------------------

def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS cases (
                id                   INTEGER PRIMARY KEY,
                title                TEXT NOT NULL,
                crime_type           TEXT NOT NULL DEFAULT '__migrated__',
                date_occurred        TEXT NOT NULL,
                address              TEXT,
                latitude             REAL,
                longitude            REAL,
                crime_scene_address  TEXT,
                crime_scene_lat      REAL,
                crime_scene_lon      REAL,
                body_found_address   TEXT,
                body_found_lat       REAL,
                body_found_lon       REAL,
                is_murder            INTEGER NOT NULL DEFAULT 0,
                victim_count         INTEGER,
                mo_description       TEXT,
                victim_profile       TEXT,
                status               TEXT NOT NULL DEFAULT 'Active',
                created_at           TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS case_crime_types (
                id         INTEGER PRIMARY KEY,
                case_id    INTEGER NOT NULL,
                crime_type TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
                UNIQUE(case_id, crime_type)
            );

            CREATE TABLE IF NOT EXISTS case_tags (
                id      INTEGER PRIMARY KEY,
                case_id INTEGER NOT NULL,
                tag     TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
                UNIQUE(case_id, tag)
            );

            CREATE TABLE IF NOT EXISTS suspects (
                id            INTEGER PRIMARY KEY,
                name          TEXT NOT NULL,
                description   TEXT,
                known_aliases TEXT,
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS suspect_crime_history (
                id                INTEGER PRIMARY KEY,
                suspect_id        INTEGER NOT NULL,
                crime_type        TEXT NOT NULL,
                date_of_crime     TEXT,
                conviction_status TEXT NOT NULL,
                notes             TEXT,
                created_at        TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (suspect_id) REFERENCES suspects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS suspect_case_links (
                id              INTEGER PRIMARY KEY,
                suspect_id      INTEGER NOT NULL,
                case_id         INTEGER NOT NULL,
                connection_type TEXT NOT NULL,
                notes           TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (suspect_id) REFERENCES suspects(id) ON DELETE CASCADE,
                FOREIGN KEY (case_id)   REFERENCES cases(id)    ON DELETE CASCADE,
                UNIQUE(suspect_id, case_id, connection_type)
            );

            CREATE TABLE IF NOT EXISTS case_links (
                id              INTEGER PRIMARY KEY,
                case_id_1       INTEGER NOT NULL,
                case_id_2       INTEGER NOT NULL,
                similarity_note TEXT NOT NULL,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (case_id_1) REFERENCES cases(id) ON DELETE CASCADE,
                FOREIGN KEY (case_id_2) REFERENCES cases(id) ON DELETE CASCADE,
                CHECK(case_id_1 < case_id_2)
            );

            CREATE TABLE IF NOT EXISTS timeline_events (
                id              INTEGER PRIMARY KEY,
                case_id         INTEGER NOT NULL,
                event_timestamp TEXT NOT NULL,
                title           TEXT NOT NULL,
                description     TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS projects (
                id          INTEGER PRIMARY KEY,
                name        TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS project_cases (
                id         INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                case_id    INTEGER NOT NULL,
                added_at   TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (case_id)    REFERENCES cases(id)    ON DELETE CASCADE,
                UNIQUE(project_id, case_id)
            );
        """)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Migration  (idempotent — safe to call on every startup)
# ---------------------------------------------------------------------------

def migrate_db() -> None:
    conn = get_connection()
    try:
        # 1. Add new columns to cases (silently skip if already present)
        new_cols = [
            "ALTER TABLE cases ADD COLUMN crime_scene_address TEXT",
            "ALTER TABLE cases ADD COLUMN crime_scene_lat REAL",
            "ALTER TABLE cases ADD COLUMN crime_scene_lon REAL",
            "ALTER TABLE cases ADD COLUMN body_found_address TEXT",
            "ALTER TABLE cases ADD COLUMN body_found_lat REAL",
            "ALTER TABLE cases ADD COLUMN body_found_lon REAL",
            "ALTER TABLE cases ADD COLUMN is_murder INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE cases ADD COLUMN victim_count INTEGER",
        ]
        for sql in new_cols:
            try:
                conn.execute(sql)
                conn.commit()
            except Exception:
                pass

        # 2. New tables — init_db already handles IF NOT EXISTS, but be safe
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS case_crime_types (
                id INTEGER PRIMARY KEY,
                case_id INTEGER NOT NULL,
                crime_type TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
                UNIQUE(case_id, crime_type)
            );
            CREATE TABLE IF NOT EXISTS case_tags (
                id INTEGER PRIMARY KEY,
                case_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
                UNIQUE(case_id, tag)
            );
            CREATE TABLE IF NOT EXISTS suspect_crime_history (
                id INTEGER PRIMARY KEY,
                suspect_id INTEGER NOT NULL,
                crime_type TEXT NOT NULL,
                date_of_crime TEXT,
                conviction_status TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (suspect_id) REFERENCES suspects(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS project_cases (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                case_id INTEGER NOT NULL,
                added_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
                UNIQUE(project_id, case_id)
            );
        """)
        conn.commit()

        # 3. Copy old single-location data → crime_scene fields
        conn.execute("""
            UPDATE cases
            SET crime_scene_address = address,
                crime_scene_lat     = latitude,
                crime_scene_lon     = longitude
            WHERE crime_scene_lat IS NULL
              AND latitude IS NOT NULL
        """)
        conn.commit()

        # 4. Migrate single crime_type → case_crime_types table
        rows = conn.execute(
            "SELECT id, crime_type FROM cases WHERE crime_type != '__migrated__'"
        ).fetchall()
        for row in rows:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO case_crime_types (case_id, crime_type, sort_order) VALUES (?, ?, 0)",
                    (row["id"], row["crime_type"]),
                )
            except Exception:
                pass
        if rows:
            conn.execute(
                "UPDATE cases SET crime_type = '__migrated__' WHERE crime_type != '__migrated__'"
            )
            conn.commit()

        # 5. Migrate old status values
        conn.execute("UPDATE cases SET status = 'Active'    WHERE status IN ('Open', 'Linked')")
        conn.execute("UPDATE cases SET status = 'Solved'    WHERE status = 'Closed'")
        conn.commit()

    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

def add_case(
    title: str,
    date_occurred: str,
    status: str = "Active",
    mo_description: str = "",
    victim_profile: str = "",
    is_murder: bool = False,
    victim_count: int | None = None,
    crime_scene_address: str = "",
    crime_scene_lat: float | None = None,
    crime_scene_lon: float | None = None,
    body_found_address: str = "",
    body_found_lat: float | None = None,
    body_found_lon: float | None = None,
) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO cases
               (title, crime_type, date_occurred, status,
                is_murder, victim_count,
                crime_scene_address, crime_scene_lat, crime_scene_lon,
                body_found_address,  body_found_lat,  body_found_lon,
                mo_description, victim_profile)
               VALUES (?, '__migrated__', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, date_occurred, status,
             int(is_murder), victim_count,
             crime_scene_address or None, crime_scene_lat, crime_scene_lon,
             body_found_address or None,  body_found_lat,  body_found_lon,
             mo_description or None, victim_profile or None),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_case(case_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_cases(project_id: int | None = None) -> list[dict]:
    conn = get_connection()
    try:
        if project_id is None:
            rows = conn.execute(
                "SELECT * FROM cases ORDER BY date_occurred DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT c.* FROM cases c
                   JOIN project_cases pc ON pc.case_id = c.id
                   WHERE pc.project_id = ?
                   ORDER BY c.date_occurred DESC""",
                (project_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_case(case_id: int, **fields) -> None:
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [case_id]
    conn = get_connection()
    try:
        conn.execute(f"UPDATE cases SET {set_clause} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def delete_case(case_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Case crime types  (many-to-many)
# ---------------------------------------------------------------------------

def set_case_crime_types(case_id: int, crime_types: list[str]) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM case_crime_types WHERE case_id = ?", (case_id,))
        for i, ct in enumerate(crime_types):
            conn.execute(
                "INSERT OR IGNORE INTO case_crime_types (case_id, crime_type, sort_order) VALUES (?, ?, ?)",
                (case_id, ct, i),
            )
        conn.commit()
    finally:
        conn.close()


def get_case_crime_types(case_id: int) -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT crime_type FROM case_crime_types WHERE case_id = ? ORDER BY sort_order ASC",
            (case_id,),
        ).fetchall()
        return [r["crime_type"] for r in rows]
    finally:
        conn.close()


def get_primary_crime_type(case_id: int) -> str | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT crime_type FROM case_crime_types WHERE case_id = ? ORDER BY sort_order ASC LIMIT 1",
            (case_id,),
        ).fetchone()
        return row["crime_type"] if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Case tags
# ---------------------------------------------------------------------------

def set_case_tags(case_id: int, tags: list[str]) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM case_tags WHERE case_id = ?", (case_id,))
        for tag in tags:
            conn.execute(
                "INSERT OR IGNORE INTO case_tags (case_id, tag) VALUES (?, ?)",
                (case_id, tag),
            )
        conn.commit()
    finally:
        conn.close()


def get_case_tags(case_id: int) -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT tag FROM case_tags WHERE case_id = ? ORDER BY id ASC",
            (case_id,),
        ).fetchall()
        return [r["tag"] for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Suspects
# ---------------------------------------------------------------------------

def add_suspect(name, description, known_aliases) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO suspects (name, description, known_aliases) VALUES (?, ?, ?)",
            (name, description, known_aliases),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_suspect(suspect_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM suspects WHERE id = ?", (suspect_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_suspects() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM suspects ORDER BY name").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_suspect(suspect_id: int, **fields) -> None:
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [suspect_id]
    conn = get_connection()
    try:
        conn.execute(f"UPDATE suspects SET {set_clause} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def delete_suspect(suspect_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM suspects WHERE id = ?", (suspect_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Suspect criminal history
# ---------------------------------------------------------------------------

def add_suspect_crime_history(
    suspect_id: int,
    crime_type: str,
    date_of_crime: str | None,
    conviction_status: str,
    notes: str = "",
) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO suspect_crime_history
               (suspect_id, crime_type, date_of_crime, conviction_status, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (suspect_id, crime_type, date_of_crime, conviction_status, notes or None),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_suspect_crime_history(suspect_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM suspect_crime_history
               WHERE suspect_id = ?
               ORDER BY date_of_crime DESC NULLS LAST, created_at DESC""",
            (suspect_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_suspect_crime_history_entry(entry_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM suspect_crime_history WHERE id = ?", (entry_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Suspect-Case links
# ---------------------------------------------------------------------------

def link_suspect_to_case(suspect_id, case_id, connection_type, notes="") -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO suspect_case_links
               (suspect_id, case_id, connection_type, notes)
               VALUES (?, ?, ?, ?)""",
            (suspect_id, case_id, connection_type, notes or None),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_suspect_links_for_case(case_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT scl.*, s.name AS suspect_name
               FROM suspect_case_links scl
               JOIN suspects s ON scl.suspect_id = s.id
               WHERE scl.case_id = ?
               ORDER BY scl.created_at DESC""",
            (case_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_cases_for_suspect(suspect_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT scl.*,
                      c.title AS case_title,
                      GROUP_CONCAT(cct.crime_type, ', ') AS crime_types
               FROM suspect_case_links scl
               JOIN cases c ON scl.case_id = c.id
               LEFT JOIN case_crime_types cct ON cct.case_id = c.id
               WHERE scl.suspect_id = ?
               GROUP BY scl.id
               ORDER BY scl.created_at DESC""",
            (suspect_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_suspect_case_link(link_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM suspect_case_links WHERE id = ?", (link_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Case links  (case ↔ case similarity)
# ---------------------------------------------------------------------------

def link_cases(id_a: int, id_b: int, similarity_note: str) -> int:
    case_id_1, case_id_2 = min(id_a, id_b), max(id_a, id_b)
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO case_links (case_id_1, case_id_2, similarity_note) VALUES (?, ?, ?)",
            (case_id_1, case_id_2, similarity_note),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_linked_cases(case_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT cl.*, c1.title AS case1_title, c2.title AS case2_title
               FROM case_links cl
               JOIN cases c1 ON cl.case_id_1 = c1.id
               JOIN cases c2 ON cl.case_id_2 = c2.id
               WHERE cl.case_id_1 = ? OR cl.case_id_2 = ?
               ORDER BY cl.created_at DESC""",
            (case_id, case_id),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_case_links(project_id: int | None = None) -> list[dict]:
    conn = get_connection()
    try:
        if project_id is None:
            rows = conn.execute(
                """SELECT cl.*, c1.title AS case1_title, c2.title AS case2_title
                   FROM case_links cl
                   JOIN cases c1 ON cl.case_id_1 = c1.id
                   JOIN cases c2 ON cl.case_id_2 = c2.id
                   ORDER BY cl.created_at DESC"""
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT cl.*, c1.title AS case1_title, c2.title AS case2_title
                   FROM case_links cl
                   JOIN cases c1 ON cl.case_id_1 = c1.id
                   JOIN cases c2 ON cl.case_id_2 = c2.id
                   WHERE EXISTS (
                       SELECT 1 FROM project_cases
                       WHERE project_id = ? AND case_id = cl.case_id_1
                   )
                   AND EXISTS (
                       SELECT 1 FROM project_cases
                       WHERE project_id = ? AND case_id = cl.case_id_2
                   )
                   ORDER BY cl.created_at DESC""",
                (project_id, project_id),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_case_link(link_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM case_links WHERE id = ?", (link_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Timeline events
# ---------------------------------------------------------------------------

def add_timeline_event(case_id, event_timestamp, title, description="") -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO timeline_events
               (case_id, event_timestamp, title, description)
               VALUES (?, ?, ?, ?)""",
            (case_id, event_timestamp, title, description or None),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_timeline_events(case_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT * FROM timeline_events
               WHERE case_id = ?
               ORDER BY event_timestamp DESC""",
            (case_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_timeline_event(event_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM timeline_events WHERE id = ?", (event_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

def add_project(name: str, description: str = "") -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (name, description or None),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_all_projects() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM projects ORDER BY name ASC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_project(project_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_project(project_id: int, **fields) -> None:
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [project_id]
    conn = get_connection()
    try:
        conn.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def delete_project(project_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
    finally:
        conn.close()


def assign_case_to_project(project_id: int, case_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO project_cases (project_id, case_id) VALUES (?, ?)",
            (project_id, case_id),
        )
        conn.commit()
    finally:
        conn.close()


def unassign_case_from_project(project_id: int, case_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM project_cases WHERE project_id = ? AND case_id = ?",
            (project_id, case_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_cases_for_project(project_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT c.* FROM cases c
               JOIN project_cases pc ON pc.case_id = c.id
               WHERE pc.project_id = ?
               ORDER BY c.date_occurred DESC""",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_project_ids_for_case(case_id: int) -> list[int]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT project_id FROM project_cases WHERE case_id = ?",
            (case_id,),
        ).fetchall()
        return [r["project_id"] for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Map-specific queries
# ---------------------------------------------------------------------------

def get_cases_with_coordinates(project_id: int | None = None) -> list[dict]:
    """Returns cases with crime_scene coordinates, including primary_crime_type."""
    conn = get_connection()
    try:
        if project_id is None:
            rows = conn.execute(
                """SELECT c.*,
                          cct.crime_type AS primary_crime_type
                   FROM cases c
                   LEFT JOIN case_crime_types cct
                          ON cct.case_id = c.id AND cct.sort_order = 0
                   WHERE c.crime_scene_lat IS NOT NULL
                     AND c.crime_scene_lon IS NOT NULL
                   ORDER BY c.date_occurred DESC"""
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT c.*,
                          cct.crime_type AS primary_crime_type
                   FROM cases c
                   JOIN project_cases pc ON pc.case_id = c.id
                   LEFT JOIN case_crime_types cct
                          ON cct.case_id = c.id AND cct.sort_order = 0
                   WHERE pc.project_id = ?
                     AND c.crime_scene_lat IS NOT NULL
                     AND c.crime_scene_lon IS NOT NULL
                   ORDER BY c.date_occurred DESC""",
                (project_id,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_linked_pairs_with_coordinates(project_id: int | None = None) -> list[dict]:
    conn = get_connection()
    try:
        base_sql = """
            SELECT cl.similarity_note,
                   c1.id AS c1_id, c1.title AS c1_title,
                   c1.crime_scene_lat AS c1_lat, c1.crime_scene_lon AS c1_lon,
                   c2.id AS c2_id, c2.title AS c2_title,
                   c2.crime_scene_lat AS c2_lat, c2.crime_scene_lon AS c2_lon
            FROM case_links cl
            JOIN cases c1 ON cl.case_id_1 = c1.id
            JOIN cases c2 ON cl.case_id_2 = c2.id
            WHERE c1.crime_scene_lat IS NOT NULL AND c1.crime_scene_lon IS NOT NULL
              AND c2.crime_scene_lat IS NOT NULL AND c2.crime_scene_lon IS NOT NULL
        """
        if project_id is None:
            rows = conn.execute(base_sql).fetchall()
        else:
            rows = conn.execute(
                base_sql + """
                  AND EXISTS (SELECT 1 FROM project_cases
                              WHERE project_id = ? AND case_id = cl.case_id_1)
                  AND EXISTS (SELECT 1 FROM project_cases
                              WHERE project_id = ? AND case_id = cl.case_id_2)
                """,
                (project_id, project_id),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
