import sqlite3
from datetime import datetime

DATABASE = "floodguard.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            accuracy REAL,
            photo_path TEXT,
            status TEXT DEFAULT 'Pending',
            remarks TEXT DEFAULT '',
            email_status TEXT DEFAULT 'Not sent',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration check for existing databases
    existing_columns = [
        col[1] for col in conn.execute("PRAGMA table_info(problems)").fetchall()
    ]

    migrations = [
        ("latitude", "ALTER TABLE problems ADD COLUMN latitude REAL"),
        ("longitude", "ALTER TABLE problems ADD COLUMN longitude REAL"),
        ("accuracy", "ALTER TABLE problems ADD COLUMN accuracy REAL"),
        ("photo_path", "ALTER TABLE problems ADD COLUMN photo_path TEXT"),
        ("created_at", "ALTER TABLE problems ADD COLUMN created_at TEXT")
    ]

    for col_name, sql_stmt in migrations:
        if col_name not in existing_columns:
            try:
                conn.execute(sql_stmt)
            except Exception:
                pass

    conn.commit()
    conn.close()


def add_problem(
    name,
    email,
    title,
    description,
    location,
    latitude=None,
    longitude=None,
    accuracy=None,
    photo_path=None
):
    conn = get_db()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor = conn.execute("""
        INSERT INTO problems
        (name, email, title, description, location, latitude, longitude, accuracy, photo_path, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        email,
        title,
        description,
        location,
        latitude,
        longitude,
        accuracy,
        photo_path,
        timestamp
    ))

    problem_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return problem_id


def get_all_problems():
    conn = get_db()
    problems = conn.execute(
        "SELECT * FROM problems ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return problems


def get_problem(problem_id):
    conn = get_db()
    problem = conn.execute(
        "SELECT * FROM problems WHERE id = ?",
        (problem_id,)
    ).fetchone()
    conn.close()
    return problem


def get_problem_for_tracking(problem_id, email):
    conn = get_db()
    problem = conn.execute(
        "SELECT * FROM problems WHERE id = ? AND LOWER(email) = LOWER(?)",
        (problem_id, email.strip())
    ).fetchone()
    conn.close()
    return problem


def update_problem(problem_id, status, remarks):
    conn = get_db()

    conn.execute("""
        UPDATE problems
        SET status = ?, remarks = ?
        WHERE id = ?
    """, (status, remarks, problem_id))

    conn.commit()
    conn.close()


def update_email_status(problem_id, email_status):
    conn = get_db()

    conn.execute("""
        UPDATE problems
        SET email_status = ?
        WHERE id = ?
    """, (email_status, problem_id))

    conn.commit()
    conn.close()
