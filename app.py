# CivicResolve - simple Python backend
# Compatible with Python 3.6

from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "complaints.db")

ALLOWED_CATEGORIES = [
    "Pothole", "Garbage", "Water Supply", "Streetlight", "Drainage", "Other"
]
ALLOWED_LANGUAGES = ["English", "Telugu", "Hindi", "Other"]
ALLOWED_STATUSES = ["Submitted", "In Progress", "Resolved"]


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()
    connection.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            language TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Submitted',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.commit()
    connection.close()


def complaint_to_dict(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "description": row["description"],
        "location": row["location"],
        "language": row["language"],
        "status": row["status"],
        "created_at": row["created_at"]
    }


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "project": "CivicResolve",
        "message": "Civic issues reporting API is running.",
        "endpoints": {
            "submit_complaint": "POST /complaints",
            "list_complaints": "GET /complaints",
            "track_complaint": "GET /complaints/<id>",
            "update_status": "PATCH /complaints/<id>/status"
        }
    })


@app.route("/complaints", methods=["POST"])
def submit_complaint():
    data = request.get_json(silent=True) or {}
    required = ["name", "category", "description", "location", "language"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]
    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing_fields": missing
        }), 400

    if data["category"] not in ALLOWED_CATEGORIES:
        return jsonify({
            "error": "Invalid category",
            "allowed_categories": ALLOWED_CATEGORIES
        }), 400

    if data["language"] not in ALLOWED_LANGUAGES:
        return jsonify({
            "error": "Invalid language",
            "allowed_languages": ALLOWED_LANGUAGES
        }), 400

    connection = get_connection()
    cursor = connection.execute("""
        INSERT INTO complaints (name, category, description, location, language)
        VALUES (?, ?, ?, ?, ?)
    """, (
        str(data["name"]).strip(),
        data["category"],
        str(data["description"]).strip(),
        str(data["location"]).strip(),
        data["language"]
    ))
    connection.commit()
    complaint_id = cursor.lastrowid
    row = connection.execute(
        "SELECT * FROM complaints WHERE id = ?", (complaint_id,)
    ).fetchone()
    connection.close()

    return jsonify({
        "message": "Complaint submitted successfully",
        "complaint": complaint_to_dict(row)
    }), 201


@app.route("/complaints", methods=["GET"])
def list_complaints():
    connection = get_connection()
    rows = connection.execute(
        "SELECT * FROM complaints ORDER BY id DESC"
    ).fetchall()
    connection.close()
    return jsonify([complaint_to_dict(row) for row in rows])


@app.route("/complaints/<int:complaint_id>", methods=["GET"])
def track_complaint(complaint_id):
    connection = get_connection()
    row = connection.execute(
        "SELECT * FROM complaints WHERE id = ?", (complaint_id,)
    ).fetchone()
    connection.close()

    if row is None:
        return jsonify({"error": "Complaint not found"}), 404
    return jsonify(complaint_to_dict(row))


@app.route("/complaints/<int:complaint_id>/status", methods=["PATCH"])
def update_status(complaint_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status", "")

    if status not in ALLOWED_STATUSES:
        return jsonify({
            "error": "Invalid status",
            "allowed_statuses": ALLOWED_STATUSES
        }), 400

    connection = get_connection()
    cursor = connection.execute(
        "UPDATE complaints SET status = ? WHERE id = ?",
        (status, complaint_id)
    )
    connection.commit()
    row = connection.execute(
        "SELECT * FROM complaints WHERE id = ?", (complaint_id,)
    ).fetchone()
    connection.close()

    if cursor.rowcount == 0:
        return jsonify({"error": "Complaint not found"}), 404
    return jsonify({
        "message": "Complaint status updated",
        "complaint": complaint_to_dict(row)
    })


if __name__ == "__main__":
    initialize_database()
    # Local development server only. Do not use Flask's debug server in production.
    app.run(host="127.0.0.1", port=5000, debug=False)
