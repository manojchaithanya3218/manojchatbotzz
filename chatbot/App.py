from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types
from dotenv import load_dotenv
import mysql.connector
import os

# ==========================
# LOAD ENVIRONMENT VARIABLES
# ==========================

load_dotenv()

app = Flask(__name__)

# ==========================
# GEMINI CLIENT
# ==========================

client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY")
)

# ==========================
# MYSQL CONNECTION
# ==========================

db = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE")
)

cursor = db.cursor()

# ==========================
# HOME PAGE
# ==========================

@app.route("/")
def index():
    return render_template("index.html")


# ==========================
# CHAT API
# ==========================

@app.route("/chat", methods=["POST"])
def chat_response():

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "error": "No data received"
            }), 400

        user_message = data.get("message")

        if not user_message:
            return jsonify({
                "error": "Message cannot be empty"
            }), 400

        user_id = 1

        # ==========================
        # SAVE USER MESSAGE
        # ==========================

        cursor.execute(
            """
            INSERT INTO chat_history
            (user_id, role, message)
            VALUES (%s,%s,%s)
            """,
            (user_id, "user", user_message)
        )

        db.commit()

        # ==========================
        # MEMORY RETRIEVAL
        # ==========================

        cursor.execute(
            """
            SELECT role,message
            FROM chat_history
            WHERE user_id=%s
            ORDER BY id DESC
            LIMIT 20
            """,
            (user_id,)
        )

        rows = cursor.fetchall()

        history = ""

        for role, message in reversed(rows):
            history += f"{role}: {message}\n"

        # ==========================
        # SMART PROMPT
        # ==========================

        prompt = f"""
You are an intelligent AI assistant.

Rules:
- Remember previous conversation.
- Use stored memory when relevant.
- If user asks their name, use memory.
- Answer accurately.
- Use Google Search when needed.
- Give concise answers unless user asks for details.

Conversation History:

{history}

Current User Message:
{user_message}
"""

        # ==========================
        # GEMINI RESPONSE
        # ==========================

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        google_search=types.GoogleSearch()
                    )
                ]
            )
        )

        bot_reply = response.text

        # ==========================
        # SAVE BOT RESPONSE
        # ==========================

        cursor.execute(
            """
            INSERT INTO chat_history
            (user_id, role, message)
            VALUES (%s,%s,%s)
            """,
            (user_id, "assistant", bot_reply)
        )

        db.commit()

        return jsonify({
            "response": bot_reply
        })

    except Exception as e:

        print("ERROR:", e)

        return jsonify({
            "error": str(e)
        }), 500


# ==========================
# CHAT HISTORY
# ==========================

@app.route("/history")
def history():

    try:

        cursor.execute(
            """
            SELECT role,message,created_at
            FROM chat_history
            ORDER BY id DESC
            LIMIT 50
            """
        )

        rows = cursor.fetchall()

        result = []

        for row in rows:
            result.append({
                "role": row[0],
                "message": row[1],
                "time": str(row[2])
            })

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# ==========================
# CLEAR MEMORY
# ==========================

@app.route("/clear")
def clear_memory():

    try:

        cursor.execute(
            """
            DELETE FROM chat_history
            WHERE user_id=%s
            """,
            (1,)
        )

        db.commit()

        return jsonify({
            "message": "Memory cleared successfully"
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ==========================
# HEALTH CHECK
# ==========================

@app.route("/health")
def health():

    return jsonify({
        "status": "running"
    })


# ==========================
# RUN APP
# ==========================

if __name__ == "__main__":
    app.run(debug=True)