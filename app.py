from __future__ import annotations

import base64
import os
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, Response, jsonify, session
from werkzeug.utils import secure_filename

# App configuration
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

# --- OpenCV camera (server-side) ---
try:
	import cv2  # type: ignore
	except_import_error = None
except Exception as e:  # pragma: no cover
	except_import_error = e
	cv2 = None  # type: ignore

from threading import Lock

class OpenCVCamera:
	def __init__(self, device_index: int = 0):
		self.device_index = device_index
		self.lock = Lock()
		self.cap = None
		self._ensure_open()

	def _ensure_open(self) -> None:
		if cv2 is None:
			return
		if self.cap is None or not self.cap.isOpened():
			# Use CAP_DSHOW on Windows for faster open
			self.cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
			# Optional: set a reasonable resolution
			if self.cap is not None and self.cap.isOpened():
				self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
				self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

	def read_jpeg_bytes(self) -> bytes | None:
		if cv2 is None:
			return None
		self._ensure_open()
		if self.cap is None or not self.cap.isOpened():
			return None
		with self.lock:
			ok, frame = self.cap.read()
			if not ok:
				return None
			# Encode as JPEG
			ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
			if not ok:
				return None
			return buf.tobytes()

	def save_snapshot(self, path: Path) -> bool:
		if cv2 is None:
			return False
		self._ensure_open()
		if self.cap is None or not self.cap.isOpened():
			return False
		with self.lock:
			ok, frame = self.cap.read()
			if not ok:
				return False
			ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
			if not ok:
				return False
			path.write_bytes(buf.tobytes())
			return True

	def release(self) -> None:
		if self.cap is not None:
			with self.lock:
				try:
					self.cap.release()
				except Exception:
					pass

# Lazy singleton
_camera: OpenCVCamera | None = None

def get_camera() -> OpenCVCamera | None:
	global _camera
	if _camera is None:
		if cv2 is None:
			return None
		_camera = OpenCVCamera()
	return _camera


def is_allowed_file(filename: str) -> bool:
	return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage) -> str | None:
	if file_storage and file_storage.filename:
		filename = secure_filename(file_storage.filename)
		if not is_allowed_file(filename):
			return None
		ext = filename.rsplit(".", 1)[1].lower()
		unique_name = f"upload_{uuid.uuid4().hex}.{ext}"
		save_path = UPLOAD_DIR / unique_name
		file_storage.save(save_path)
		return unique_name
	return None


def save_camera_data_url(data_url: str) -> str | None:
	"""Accepts a data URL like 'data:image/png;base64,AAAA', saves it, and returns filename."""
	if not data_url or not data_url.startswith("data:image"):
		return None
	try:
		header, b64data = data_url.split(",", 1)
		# Determine extension from header
		ext = "png"
		if "/jpeg" in header or "/jpg" in header:
			ext = "jpg"
		elif "/webp" in header:
			ext = "webp"
		binary = base64.b64decode(b64data)
		unique_name = f"camera_{uuid.uuid4().hex}.{ext}"
		save_path = UPLOAD_DIR / unique_name
		with open(save_path, "wb") as f:
			f.write(binary)
		return unique_name
	except Exception:
		return None


def compute_assessment_percentage(answers: Dict[str, int]) -> Tuple[int, Dict[str, int]]:
	"""Compute percentage based on 0..3 scale for each answer.
	Returns (percentage, totals_by_category).
	"""
	# Define categories by key prefix
	categories = {
		"communication": [],
		"behaviour": [],
		"social": [],
	}
	for key, value in answers.items():
		for cat in categories.keys():
			if key.startswith(f"{cat}_"):
				categories[cat].append(value)

	totals_by_category: Dict[str, int] = {}
	max_per_question = 3
	for cat, values in categories.items():
		if values:
			totals_by_category[cat] = sum(values)
		else:
			totals_by_category[cat] = 0

	total_score = sum(totals_by_category.values())
	num_questions = sum(len(v) for v in categories.values())
	max_score = num_questions * max_per_question if num_questions > 0 else 1
	percentage = round((total_score / max_score) * 100)
	return percentage, totals_by_category


# Image analysis helper removed


@app.route("/")
def index():
	return render_template("index.html")


@app.route("/assessment", methods=["GET"]) 
def assessment():
	return render_template("assessment.html")


@app.route("/video_feed")
def video_feed():
	"""MJPEG stream from OpenCV camera."""
	camera = get_camera()
	if camera is None:
		return "OpenCV not available on server", 503

	def generate():
		while True:
			frame = camera.read_jpeg_bytes()
			if frame is None:
				break
			yield (b"--frame\r\n"
				b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

	return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/capture", methods=["POST"]) 
def capture_snapshot():
	"""Capture one frame using OpenCV and save to uploads; returns JSON with filename."""
	camera = get_camera()
	if camera is None:
		return jsonify({"error": "OpenCV not available"}), 503
	unique_name = f"camera_{uuid.uuid4().hex}.jpg"
	save_path = UPLOAD_DIR / unique_name
	success = camera.save_snapshot(save_path)
	if not success:
		return jsonify({"error": "Failed to capture image"}), 500
	return jsonify({"filename": unique_name, "url": url_for("uploads", filename=unique_name)})


@app.route("/submit", methods=["POST"]) 
def submit():
	# Collect questionnaire answers
	answers: Dict[str, int] = {}
	for prefix in ["communication", "behaviour", "social"]:
		for i in range(1, 6):
			field_name = f"{prefix}_{i}"
			try:
				answers[field_name] = int(request.form.get(field_name, "0"))
			except ValueError:
				answers[field_name] = 0

	# Handle file upload
	uploaded_filename: str | None = None
	photo_file = request.files.get("photo")
	uploaded_filename = save_uploaded_file(photo_file)
	if photo_file and not uploaded_filename:
		flash("Unsupported image type. Allowed: png, jpg, jpeg, webp.", "warning")

	# Handle camera snapshot: OpenCV filename or legacy data URL
	camera_filename_form = request.form.get("camera_image_filename", "").strip()
	camera_data_url = request.form.get("camera_image_data", "")
	camera_filename = None
	if camera_filename_form:
		camera_filename = camera_filename_form
	elif camera_data_url:
		camera_filename = save_camera_data_url(camera_data_url)

	percentage, totals_by_category = compute_assessment_percentage(answers)

	# Optionally adjust percentage if at least one image was received (no ML, just a placeholder tweak)
	if uploaded_filename or camera_filename:
		percentage = min(100, percentage)  # keep as-is; no diagnostic weighting

	evidence_files: List[str] = []
	if uploaded_filename:
		evidence_files.append(uploaded_filename)
	if camera_filename:
		evidence_files.append(camera_filename)

	return render_template(
		"result.html",
		percentage=percentage,
		totals_by_category=totals_by_category,
		evidence_files=evidence_files,
	)


@app.route("/uploads/<path:filename>")
def uploads(filename: str):
	return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# --- Prediction API ---
@app.route("/api/predict_image", methods=["POST"]) 
def api_predict_image():
    file = request.files.get("image")
    if not file or not file.filename:
        return jsonify({"error": "No image provided"}), 400
    filename = save_uploaded_file(file)
    if not filename:
        return jsonify({"error": "Unsupported image type. Allowed: png, jpg, jpeg, webp."}), 400
    image_path = UPLOAD_DIR / filename
    try:
        from ml_model import predict_image  # lazy import to avoid startup failures
        percentage, _label = predict_image(str(image_path))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({
        "autism_percentage": percentage
    })


# Image module routes removed


# --- Simple rule-based chatbot ---

def generate_chatbot_reply(message: str) -> str:
	text = (message or "").lower().strip()
	if not text:
		return "Hi! Ask me about symptoms, treatment, diagnosis, scoring, privacy, or the camera."
	keywords_to_responses = [
		(["hello", "hi", "hey"], "Hello! How can I help with the assessment?"),
		(["symptom", "sign", "signs", "red flag"], (
			"Common characteristics can include: differences in social communication (eye contact, back-and-forth conversation), "
			"restricted or repetitive behaviors, strong interests/routines, and sensory sensitivities. Every person is different. "
			"If you have concerns, please consult a qualified clinician for evaluation."
		)),
		(["treatment", "therapy", "therapies", "intervention"], (
			"There is no single ‘cure’, but evidence-based supports can help: behavioral therapies (e.g., ABA variants), "
			"speech-language therapy, occupational therapy (including sensory integration), social skills training, parent-mediated "
			"interventions, and school-based supports/IEPs. Early, individualized interventions are most effective."
		)),
		(["diagnosis", "diagnose", "screening", "assessment", "test"], (
			"Diagnosis typically involves: (1) developmental screening (e.g., questionnaires such as M-CHAT-R/F for toddlers), "
			"and (2) a comprehensive evaluation by qualified professionals using standardized tools (e.g., ADOS-2, ADI-R), "
			"plus hearing/vision and developmental history. This app is not diagnostic—please see a healthcare professional."
		)),
		(["score", "percentage", "result"], "The percentage is computed from your answers on a 0–3 scale across communication, behaviour, and social questions."),
		(["privacy", "data", "upload"], "Photos are saved locally in the server’s uploads folder and are not shared externally by this demo."),
		(["camera", "webcam", "live"], "If streaming fails, close other apps using the webcam and ensure the server can access it. On Windows, only one app can use the camera at a time."),
		(["opencv", "stream", "capture"], "OpenCV serves an MJPEG stream at /video_feed and captures snapshots with the Capture button."),
		(["cause", "causes", "risk"], "Autism has multifactorial causes (genetic + environmental). Evidence shows vaccines do not cause autism."),
		(["retake", "again", "restart"], "You can retake the assessment anytime from the Assessment page."),
		(["autism", "asd"], "Autism spectrum disorder is a neurodevelopmental condition. For clinical guidance, talk with a qualified professional."),
	]
	for keys, resp in keywords_to_responses:
		if any(k in text for k in keys):
			return resp
	return (
		"I can share general information about symptoms, treatment/therapies, and diagnosis/screening, "
		"plus how to use this app. For medical concerns, please consult a qualified professional."
	)


@app.route("/chat", methods=["GET"])
def chat():
	chat_history = session.get("chat_history", [])
	return render_template("chat.html", chat_history=chat_history)


@app.route("/chat_message", methods=["POST"]) 
def chat_message():
	payload = request.get_json(silent=True) or {}
	user_text = (payload.get("message") or request.form.get("message") or "").strip()
	reply = generate_chatbot_reply(user_text)
	chat_history = session.get("chat_history", [])
	chat_history.append({"role": "user", "content": user_text})
	chat_history.append({"role": "assistant", "content": reply})
	# keep history limited
	session["chat_history"] = chat_history[-50:]
	return jsonify({"reply": reply})


if __name__ == "__main__":
	port = int(os.environ.get("PORT", 5000))
	app.run(host="0.0.0.0", port=port, debug=True)
