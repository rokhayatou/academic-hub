import json
import sqlite3

def load_major(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)

    major = data["major"]
    conn = sqlite3.connect("academic_hub.db")

    for group in data["requirement_groups"]:
        cursor = conn.execute(
            "INSERT INTO requirements (major, group_name, req_type, credits_needed) VALUES (?, ?, ?, ?)",
            (major, group["group_name"], group["type"], group.get("credits_needed"))
        )
        requirement_id = cursor.lastrowid

        if group["type"] == "sequence":
            for dept, courses in group["sequences"].items():
                for course_code in courses:
                    conn.execute(
                        "INSERT INTO requirement_options (requirement_id, course_code, sequence_group) VALUES (?, ?, ?)",
                        (requirement_id, course_code, dept)
                    )
        else:
            for course_code in group.get("courses", []):
                conn.execute(
                    "INSERT INTO requirement_options (requirement_id, course_code, is_substitution) VALUES (?, ?, ?)",
                    (requirement_id, course_code, 0)
                )
            for course_code in group.get("substitution_courses", []):
                conn.execute(
                    "INSERT INTO requirement_options (requirement_id, course_code, is_substitution) VALUES (?, ?, ?)",
                    (requirement_id, course_code, 1)
                )

    conn.commit()
    conn.close()
    print(f"Loaded {major} requirements successfully.")

if __name__ == "__main__":
    load_major("cs_major.json")
