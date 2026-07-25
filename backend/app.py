import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        dbname=os.getenv("DB_NAME", "bd_server"),
        user=os.getenv("DB_USER", "daniel_user"),
        password=os.getenv("DB_PASSWORD", ""),
        port=os.getenv("DB_PORT", "5432"),
        row_factory=dict_row,
    )


# LISTAR todas las tareas (con soporte de filtro opcional ?q=texto)
@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    query_text = request.args.get("q", "").strip()
    conn = get_connection()
    cur = conn.cursor()
    if query_text:
        cur.execute(
            "SELECT * FROM tasks WHERE title ILIKE %s ORDER BY created_at DESC",
            (f"%{query_text}%",),
        )
    else:
        cur.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(tasks)


# INSERTAR una nueva tarea
@app.route("/api/tasks", methods=["POST"])
def add_task():
    data = request.get_json()
    title = data.get("title", "").strip()
    fecha_limite = data.get("fecha_limite")  # opcional, puede venir vacío
    if not title:
        return jsonify({"error": "El título no puede estar vacío"}), 400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (title, fecha_limite) VALUES (%s, %s) RETURNING *",
        (title, fecha_limite),
    )
    new_task = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return jsonify(new_task), 201


# ACTUALIZAR una tarea (texto y/o estado completado)
@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    data = request.get_json()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
    existing = cur.fetchone()
    if not existing:
        cur.close()
        conn.close()
        return jsonify({"error": "Tarea no encontrada"}), 404

    title = data.get("title", existing["title"])
    completed = data.get("completed", existing["completed"])
    fecha_limite = data.get("fecha_limite", existing.get("fecha_limite"))

    cur.execute(
        "UPDATE tasks SET title = %s, completed = %s, fecha_limite = %s WHERE id = %s RETURNING *",
        (title, completed, fecha_limite, task_id),
    )
    updated_task = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return jsonify(updated_task)


# ELIMINAR una tarea
@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    deleted_count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()

    if deleted_count == 0:
        return jsonify({"error": "Tarea no encontrada"}), 404
    return jsonify({"message": "Tarea eliminada"}), 200


# Chequeo rápido de que el servidor está vivo
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
