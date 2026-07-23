import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "mysecretkey"

USER_FILE = "users.txt"
MARKS_FILE = "marks.json"
ATTENDANCE_FILE = "attendance.json"

DEFAULT_USERS = [
    {"username": "admin", "password": "admin123", "role": "admin", "name": "Administrator"},
    {"username": "vishnupriya", "password": "dbms123", "role": "faculty", "name": "Vishnupriya", "subject": "DBMS"},
    {"username": "selvakumar", "password": "os123", "role": "faculty", "name": "Selvakumar", "subject": "Operating System"},
    {"username": "janet", "password": "cn123", "role": "faculty", "name": "Janet", "subject": "Computer Networks"},
    {"username": "bhopche", "password": "java123", "role": "faculty", "name": "Bhopche", "subject": "Java"},
    {"username": "student1", "password": "123", "role": "student", "name": "Alex Smith"}
]

# JSON Data Handlers
def load_json(filepath):
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            json.dump([], f)
        return []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

# User File Handlers
def load_users():
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, "w") as f:
            for u in DEFAULT_USERS:
                subj = u.get("subject", "N/A")
                f.write(f"{u['username']},{u['password']},{u['role']},{u.get('name', u['username'])},{subj}\n")

    users = []
    with open(USER_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(",")
                if len(parts) >= 3:
                    users.append({
                        "username": parts[0],
                        "password": parts[1],
                        "role": parts[2],
                        "name": parts[3] if len(parts) > 3 else parts[0],
                        "subject": parts[4] if len(parts) > 4 else "N/A"
                    })
    return users

def save_all_users(users_list):
    with open(USER_FILE, "w") as f:
        for u in users_list:
            f.write(f"{u['username']},{u['password']},{u['role']},{u['name']},{u.get('subject', 'N/A')}\n")

def save_user(username, password, role="student", name="", subject="N/A"):
    with open(USER_FILE, "a") as f:
        f.write(f"\n{username},{password},{role},{name or username},{subject}")

@app.route("/")
def home():
    if "username" in session:
        return redirect(url_for(session["role"]))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        name = request.form.get("name", "").strip()

        users = load_users()
        if any(u["username"].lower() == username.lower() for u in users):
            flash("Username already exists!", "danger")
            return render_template("register.html")

        save_user(username, password, "student", name)
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        users = load_users()
        for user in users:
            if user["username"].lower() == username.lower() and user["password"] == password:
                session["username"] = user["username"]
                session["role"] = user["role"]
                session["name"] = user["name"]
                return redirect(url_for(user["role"]))

        flash("Invalid Username or Password", "danger")

    return render_template("login.html")

# --- STUDENT ROUTE ---
@app.route("/student")
def student():
    if "username" not in session or session["role"] != "student":
        return redirect(url_for("unauthorized" if "username" in session else "login"))

    username = session["username"]
    all_marks = load_json(MARKS_FILE)
    all_attendance = load_json(ATTENDANCE_FILE)
    users = load_users()

    faculty_list = [u for u in users if u["role"] == "faculty"]
    subjects = sorted(list(set([f["subject"] for f in faculty_list if f.get("subject") and f["subject"] != "N/A"])))

    student_report = []
    chart_labels = []
    chart_data = []

    for subj in subjects:
        m_entry = next((m for m in all_marks if m.get("username", "").lower() == username.lower() and m.get("subject") == subj), None)
        a_entry = next((a for a in all_attendance if a.get("username", "").lower() == username.lower() and a.get("subject") == subj), None)

        marks_val = m_entry["marks"] if m_entry else "Not Updated"
        att_str = a_entry["attendance"] if a_entry else "Not Updated"

        att_num = 0
        if a_entry:
            try:
                att_num = float(str(a_entry["attendance"]).replace("%", "").strip())
            except ValueError:
                att_num = 0

        student_report.append({
            "subject": subj,
            "marks": marks_val,
            "attendance": att_str
        })

        if a_entry:
            chart_labels.append(subj)
            chart_data.append(att_num)

    return render_template(
        "student.html",
        user=session,
        report=student_report,
        chart_labels=chart_labels,
        chart_data=chart_data
    )

# --- FACULTY ROUTE ---
@app.route("/faculty", methods=["GET", "POST"])
def faculty():
    if "username" not in session or session["role"] != "faculty":
        return redirect(url_for("unauthorized" if "username" in session else "login"))

    users = load_users()
    faculty_user = next((u for u in users if u["username"] == session["username"]), {})
    subject = faculty_user.get("subject", "General")
    students = [u for u in users if u["role"] == "student"]

    if request.method == "POST":
        student_user = request.form.get("student_username", "").strip()
        marks_val = request.form.get("marks", "").strip()
        attendance_val = request.form.get("attendance", "").strip()

        if student_user:
            # Update Marks
            marks_list = load_json(MARKS_FILE)
            marks_list = [m for m in marks_list if not (m.get("username", "").lower() == student_user.lower() and m.get("subject") == subject)]
            if marks_val:
                marks_list.append({"username": student_user, "subject": subject, "marks": marks_val})
            save_json(MARKS_FILE, marks_list)

            # Update Attendance
            att_list = load_json(ATTENDANCE_FILE)
            att_list = [a for a in att_list if not (a.get("username", "").lower() == student_user.lower() and a.get("subject") == subject)]
            if attendance_val:
                att_list.append({"username": student_user, "subject": subject, "attendance": attendance_val})
            save_json(ATTENDANCE_FILE, att_list)

            flash(f"Updated records for @{student_user} successfully!", "success")
        return redirect(url_for("faculty"))

    marks_data = {m["username"]: m["marks"] for m in load_json(MARKS_FILE) if m.get("subject") == subject}
    att_data = {a["username"]: a["attendance"] for a in load_json(ATTENDANCE_FILE) if a.get("subject") == subject}

    return render_template(
        "faculty.html",
        user=session,
        faculty_info=faculty_user,
        students=students,
        marks_data=marks_data,
        att_data=att_data
    )

# --- ADMIN ROUTES ---
@app.route("/admin")
def admin():
    if "username" not in session or session["role"] != "admin":
        return redirect(url_for("unauthorized" if "username" in session else "login"))

    all_users = load_users()
    students = [u for u in all_users if u["role"] == "student"]
    faculties = [u for u in all_users if u["role"] == "faculty"]

    # Gather list of unique subjects
    subjects = sorted(list(set([f["subject"] for f in faculties if f.get("subject") and f["subject"] != "N/A"])))

    all_marks = load_json(MARKS_FILE)
    all_attendance = load_json(ATTENDANCE_FILE)

    return render_template(
        "admin.html",
        user=session,
        users=all_users,
        students=students,
        faculties=faculties,
        subjects=subjects,
        marks=all_marks,
        attendance=all_attendance
    )

@app.route("/admin/delete_user/<username>", methods=["POST"])
def delete_user(username):
    if "username" not in session or session["role"] != "admin":
        return redirect(url_for("unauthorized"))

    users = load_users()
    # Filter out target user
    updated_users = [u for u in users if u["username"].lower() != username.lower()]

    # Save back to file
    save_all_users(updated_users)

    # Clean up their marks and attendance records
    all_marks = [m for m in load_json(MARKS_FILE) if m.get("username", "").lower() != username.lower()]
    save_json(MARKS_FILE, all_marks)

    all_att = [a for a in load_json(ATTENDANCE_FILE) if a.get("username", "").lower() != username.lower()]
    save_json(ATTENDANCE_FILE, all_att)

    flash(f"User @{username} deleted successfully!", "success")
    return redirect(url_for("admin"))

@app.route("/admin/update_marks", methods=["POST"])
def admin_update_marks():
    if "username" not in session or session["role"] != "admin":
        return redirect(url_for("unauthorized"))

    student_user = request.form.get("student_username", "").strip()
    subject = request.form.get("subject", "").strip()
    marks_val = request.form.get("marks", "").strip()
    attendance_val = request.form.get("attendance", "").strip()

    if student_user and subject:
        # Update Marks
        marks_list = load_json(MARKS_FILE)
        marks_list = [m for m in marks_list if not (m.get("username", "").lower() == student_user.lower() and m.get("subject") == subject)]
        if marks_val:
            marks_list.append({"username": student_user, "subject": subject, "marks": marks_val})
        save_json(MARKS_FILE, marks_list)

        # Update Attendance
        att_list = load_json(ATTENDANCE_FILE)
        att_list = [a for a in att_list if not (a.get("username", "").lower() == student_user.lower() and a.get("subject") == subject)]
        if attendance_val:
            att_list.append({"username": student_user, "subject": subject, "attendance": attendance_val})
        save_json(ATTENDANCE_FILE, att_list)

        flash(f"Admin override saved for @{student_user} in {subject}!", "success")

    return redirect(url_for("admin"))

@app.route("/unauthorized")
def unauthorized():
    return render_template("unauthorized.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
