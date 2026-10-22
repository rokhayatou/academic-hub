import os, sys, subprocess, sqlite3

db = os.environ.setdefault("DB_PATH", "demo.db")
if os.path.exists(db):
    os.remove(db)

import main  # creates the empty tables via init_db()
subprocess.run([sys.executable, "load_major.py"], check=True)

conn = sqlite3.connect(db)
codes = [r[0] for r in conn.execute(
    "SELECT o.course_code FROM requirement_options o "
    "JOIN requirements r ON r.id = o.requirement_id "
    "WHERE r.req_type = 'fixed' ORDER BY o.id")]

grades = ["A", "A-", "B+", "B", "A", "B+", "A-", "B"]
for i, code in enumerate(codes[:10]):
    if not conn.execute("SELECT 1 FROM courses WHERE code = ?", (code,)).fetchone():
        conn.execute("INSERT INTO courses (code, name, credits) VALUES (?, ?, 3)", (code, code))
    if i < 8:
        conn.execute(
            "INSERT INTO completed_courses (course_code, grade, semester, status) VALUES (?, ?, ?, 'completed')",
            (code, grades[i], "Fall 2025" if i < 4 else "Spring 2026"))
    else:
        conn.execute(
            "INSERT INTO completed_courses (course_code, grade, semester, status) VALUES (?, NULL, 'Fall 2026', 'in_progress')",
            (code,))
conn.commit()
print("Demo database ready:", db, "with", min(len(codes), 10), "demo courses")
