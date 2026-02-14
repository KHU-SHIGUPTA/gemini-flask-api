from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
import os

load_dotenv()

# IMPORTANT: Must match Render environment variable
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health():
    return "Gemini API is running"

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt") or data.get("input")

    if not prompt:
        return jsonify(success=False, message="Prompt required"), 400

    try:
        response = model.generate_content(prompt)
        return jsonify(success=True, text=response.text)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


if __name__ == "__main__":
    app.run()

