from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "school_tracker_secret_key"

DATABASE = "school_tracker.db"

UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_name TEXT NOT NULL,
            location TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            description TEXT NOT NULL,
            image TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ---------------- FILE CHECK ----------------

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ---------------- HOME ----------------

@app.route("/")
def home():

    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) FROM complaints"
    ).fetchone()[0]

    pending = conn.execute(
        "SELECT COUNT(*) FROM complaints WHERE status='Pending'"
    ).fetchone()[0]

    progress = conn.execute(
        "SELECT COUNT(*) FROM complaints WHERE status='In Progress'"
    ).fetchone()[0]

    resolved = conn.execute(
        "SELECT COUNT(*) FROM complaints WHERE status='Resolved'"
    ).fetchone()[0]

    recent = conn.execute(
        "SELECT * FROM complaints ORDER BY id DESC LIMIT 5"
    ).fetchall()

    conn.close()

    return render_template(
        "index.html",
        total=total,
        pending=pending,
        progress=progress,
        resolved=resolved,
        recent=recent
    )


# ---------------- REPORT PROBLEM ----------------

@app.route("/report", methods=["GET", "POST"])
def report():

    if request.method == "POST":

        school_name = request.form["school_name"]
        location = request.form["location"]
        category = request.form["category"]
        priority = request.form["priority"]
        description = request.form["description"]

        image = request.files.get("image")
        filename = None

        if image and image.filename:

            if allowed_file(image.filename):

                filename = secure_filename(image.filename)

                # prevent duplicate filenames
                base, ext = os.path.splitext(filename)

                counter = 1
                original = filename

                while os.path.exists(
                    os.path.join(app.config["UPLOAD_FOLDER"], filename)
                ):
                    filename = f"{base}_{counter}{ext}"
                    counter += 1

                image.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        filename
                    )
                )

            else:
                flash("Invalid image format.", "danger")
                return redirect(url_for("report"))

        conn = get_db()

        conn.execute("""
            INSERT INTO complaints
            (school_name, location, category, priority, description, image)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            school_name,
            location,
            category,
            priority,
            description,
            filename
        ))

        conn.commit()

        complaint_id = conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        conn.close()

        flash(
            f"Complaint submitted successfully! Complaint ID: GS-{complaint_id}",
            "success"
        )

        return redirect(url_for("track"))

    return render_template("report.html")


# ---------------- TRACK COMPLAINT ----------------

@app.route("/track")
def track():

    search = request.args.get("search", "")

    conn = get_db()

    if search:

        complaints = conn.execute("""
            SELECT * FROM complaints
            WHERE CAST(id AS TEXT) LIKE ?
            OR school_name LIKE ?
            OR category LIKE ?
            ORDER BY id DESC
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        )).fetchall()

    else:

        complaints = conn.execute(
            "SELECT * FROM complaints ORDER BY id DESC"
        ).fetchall()

    conn.close()

    return render_template(
        "track.html",
        complaints=complaints,
        search=search
    )


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin")
def admin():

    conn = get_db()

    complaints = conn.execute(
        "SELECT * FROM complaints ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        complaints=complaints
    )


# ---------------- UPDATE STATUS ----------------

@app.route("/update/<int:complaint_id>", methods=["POST"])
def update_status(complaint_id):

    status = request.form["status"]

    conn = get_db()

    conn.execute("""
        UPDATE complaints
        SET status=?
        WHERE id=?
    """, (
        status,
        complaint_id
    ))

    conn.commit()
    conn.close()

    flash("Complaint status updated.", "success")

    return redirect(url_for("admin"))


# ---------------- DELETE ----------------

@app.route("/delete/<int:complaint_id>", methods=["POST"])
def delete_complaint(complaint_id):

    conn = get_db()

    complaint = conn.execute(
        "SELECT image FROM complaints WHERE id=?",
        (complaint_id,)
    ).fetchone()

    if complaint and complaint["image"]:

        image_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            complaint["image"]
        )

        if os.path.exists(image_path):
            os.remove(image_path)

    conn.execute(
        "DELETE FROM complaints WHERE id=?",
        (complaint_id,)
    )

    conn.commit()
    conn.close()

    flash("Complaint deleted.", "success")

    return redirect(url_for("admin"))


# ---------------- RUN ----------------

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
    