from fastapi import FastAPI
import sqlite3

app = FastAPI()


def get_db_connection():
    conn = sqlite3.connect("academic_hub.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            credits INTEGER NOT NULL,
            grade TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS completed_courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT NOT NULL,
            grade TEXT,
            semester TEXT,
            status TEXT DEFAULT 'completed'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            major TEXT NOT NULL,
            group_name TEXT NOT NULL,
            req_type TEXT NOT NULL,
            credits_needed INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS requirement_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requirement_id INTEGER NOT NULL,
            course_code TEXT NOT NULL,
            is_substitution INTEGER DEFAULT 0,
            sequence_group TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


@app.get("/")
def read_root():
    return {"message": "Hello, Academic Hub!"}


@app.post("/courses")
def add_course(code: str, name: str, credits: int, grade: str = None):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO courses (code, name, credits, grade) VALUES (?, ?, ?, ?)",
        (code, name, credits, grade)
    )
    conn.commit()
    conn.close()
    return {"message": f"Course {code} added"}


@app.get("/courses")
def list_courses():
    conn = get_db_connection()
    courses = conn.execute("SELECT * FROM courses").fetchall()
    conn.close()
    return [dict(course) for course in courses]


@app.post("/completed_courses")
def add_completed_course(course_code: str, grade: str = None, semester: str = None, status: str = "completed", credits: int = None):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO completed_courses (course_code, grade, semester, status) VALUES (?, ?, ?, ?)",
        (course_code, grade, semester, status)
    )
    if credits is not None:
        existing = conn.execute("SELECT id FROM courses WHERE code = ?", (course_code,)).fetchone()
        if existing:
            conn.execute("UPDATE courses SET credits = ? WHERE code = ?", (credits, course_code))
        else:
            conn.execute("INSERT INTO courses (code, name, credits) VALUES (?, ?, ?)", (course_code, course_code, credits))
    conn.commit()
    conn.close()
    return {"message": f"{course_code} marked as {status}"}


@app.get("/completed_courses")
def list_completed_courses():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM completed_courses").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/audit")
def audit_degree(major: str = "CS_BS"):
    conn = get_db_connection()

    completed = conn.execute("SELECT course_code, grade, status FROM completed_courses").fetchall()
    completed_codes = [r["course_code"] for r in completed if r["status"] == "completed"]
    in_progress_codes = [r["course_code"] for r in completed if r["status"] == "in_progress"]

    course_credits = {r["code"]: r["credits"] for r in conn.execute("SELECT code, credits FROM courses").fetchall()}

    requirements = conn.execute(
        "SELECT * FROM requirements WHERE major = ?", (major,)
    ).fetchall()

    results = []

    for req in requirements:
        options = conn.execute(
            "SELECT course_code, is_substitution, sequence_group FROM requirement_options WHERE requirement_id = ?",
            (req["id"],)
        ).fetchall()
        option_codes = [r["course_code"] for r in options]

        if req["req_type"] == "fixed":
            if option_codes[0] in completed_codes:
                status = "satisfied"
            elif option_codes[0] in in_progress_codes:
                status = "in_progress"
            else:
                status = "not_started"

        elif req["req_type"] == "either_or":
            if any(c in completed_codes for c in option_codes):
                status = "satisfied"
            elif any(c in in_progress_codes for c in option_codes):
                status = "in_progress"
            else:
                status = "not_started"

        elif req["req_type"] == "sequence":
            departments = {}
            for r in options:
                departments.setdefault(r["sequence_group"], []).append(r["course_code"])
            status = "not_started"
            for dept, dept_courses in departments.items():
                done = [c for c in dept_courses if c in completed_codes]
                if len(done) == len(dept_courses):
                    status = "satisfied"
                    break
                if done or any(c in in_progress_codes for c in dept_courses):
                    status = "in_progress"

        elif req["req_type"] == "credit_pool":
            regular = [r["course_code"] for r in options if not r["is_substitution"]]
            subs = [r["course_code"] for r in options if r["is_substitution"]]
            matched = [c for c in regular if c in completed_codes]
            done_subs = [c for c in subs if c in completed_codes]
            if done_subs:
                matched.append(done_subs[0])
            earned_credits = sum(course_credits.get(c, 0) for c in matched)
            needed = req["credits_needed"]
            if earned_credits >= needed:
                status = "satisfied"
            elif earned_credits > 0:
                status = "in_progress"
            else:
                status = "not_started"

        else:
            status = "unknown_type"

        results.append({
            "group_name": req["group_name"],
            "type": req["req_type"],
            "status": status
        })

    conn.close()
    return {"major": major, "requirements": results}


@app.delete("/completed_courses/{entry_id}")
def delete_completed_course(entry_id: int):
    conn = get_db_connection()
    conn.execute("DELETE FROM completed_courses WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    return {"message": f"Entry {entry_id} deleted"}


from fastapi.responses import FileResponse


@app.get("/app")
def serve_frontend():
    return FileResponse("index.html")
