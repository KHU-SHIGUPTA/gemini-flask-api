from flask import (
    Flask,
    render_template,
    request,
    Response,
    stream_with_context,
    jsonify,
)
from werkzeug.utils import secure_filename
from PIL import Image
import io
from dotenv import load_dotenv
import os

from google import genai

# Load environment variables from .env file
load_dotenv()

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
chat_session = client.chats.create(model="gemini-2.5-flash")

app = Flask(__name__, static_folder='static', template_folder='templates')

next_message = ""
next_image = ""


def allowed_file(filename):
    """Returns if a filename is supported via its extension"""
    _, ext = os.path.splitext(filename)
    return ext.lstrip('.').lower() in ALLOWED_EXTENSIONS


@app.route("/upload", methods=["POST"])
def upload_file():
    """Takes in a file, checks if it is valid,
    and saves it for the next request to the API
    """
    global next_image

    if "file" not in request.files:
        return jsonify(success=False, message="No file part")

    file = request.files["file"]

    if file.filename == "":
        return jsonify(success=False, message="No selected file")
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        # Read the file stream into a BytesIO object
        file_stream = io.BytesIO(file.read())
        file_stream.seek(0)
        next_image = Image.open(file_stream)

        return jsonify(
            success=True,
            message="File uploaded successfully and added to the conversation",
            filename=filename,
        )
    return jsonify(success=False, message="File type not allowed")


@app.route("/", methods=["GET"])
def index():
    """Renders the main homepage for the app"""
    return render_template("index.html", chat_history=chat_session.get_history())


@app.route("/chat", methods=["POST"])
def chat():
    """
    Takes in the message the user wants to send
    to the Gemini API, saves it
    """
    global next_message
    next_message = request.json["message"]
    print(chat_session.get_history())

    return jsonify(success=True)


@app.route("/stream", methods=["GET"])
def stream():
    """
    Streams the response from the server for
    both multi-modal and plain text requests
    """
    def generate():
        global next_message
        global next_image
        assistant_response_content = ""

        if next_image != "":
            response = chat_session.send_message_stream([next_message, next_image])
            next_image = ""
        else:
            response = chat_session.send_message_stream(next_message)
            next_message = ""

        for chunk in response:
            assistant_response_content += chunk.text
            yield f"data: {chunk.text}\n\n"

    return Response(stream_with_context(generate()),
                    mimetype="text/event-stream")


@app.route("/generate", methods=["POST"])
def generate():
    """
    Simple JSON API for your Node backend.
    Expects: { "input": "some prompt here" }
    Returns: { "text": "full generated email text" }
    """
    global chat_session

    data = request.get_json(silent=True) or {}
    prompt = data.get("input") or data.get("prompt")

    if not prompt:
        return jsonify(
            success=False,
            message="Missing 'input' or 'prompt' in JSON body",
        ), 400

    try:
        # Use streaming like your /stream route, but accumulate text and return once.
        assistant_response_content = ""

        response = chat_session.send_message_stream(prompt)

        for chunk in response:
            assistant_response_content += chunk.text

        return jsonify(
            success=True,
            text=assistant_response_content
        ), 200

    except Exception as e:
        print("Error in /generate:", e)
        return jsonify(
            success=False,
            message="Failed to generate text",
            error=str(e),
        ), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
