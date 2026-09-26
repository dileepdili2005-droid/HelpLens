import os
import uuid
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from config import Config
import database
import ocr_service
import ai_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("helplens")

# Initialize Flask App
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)

# Initialize database schema
database.init_db()

def allowed_file(filename):
    """Check if the uploaded file has a permitted extension."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS

@app.route("/")
def index():
    """Render the HelpLens modern single-page dashboard."""
    gemini_configured = bool(Config.GEMINI_API_KEY)
    return render_template("index.html", gemini_configured=gemini_configured)

@app.route("/api/health", methods=["GET"])
def health_check():
    """System health and capabilities check."""
    return jsonify({
        "status": "healthy",
        "app_name": "HelpLens",
        "version": "1.0.0",
        "gemini_api_configured": bool(Config.GEMINI_API_KEY),
        "tesseract_ocr_available": ocr_service.TESSERACT_AVAILABLE,
        "database_enabled": Config.USE_DATABASE,
        "active_model": Config.GEMINI_MODEL
    })

@app.route("/api/analyze", methods=["POST"])
def analyze_problem():
    """
    Main assistance pipeline:
    User Input -> Image/Text Preprocessing & OCR -> Gemini AI Analysis -> Database Storage -> Guided Response
    """
    try:
        # Extract form parameters
        problem_text = request.form.get("problem_text", "").strip()
        category = request.form.get("category", "General").strip()
        urgency = request.form.get("urgency", "Standard").strip()
        custom_api_key = request.form.get("custom_api_key", "").strip()
        
        # Check if an image was uploaded
        image_file = request.files.get("image")
        image_saved_path = None
        saved_filename = None
        ocr_result = {"text": "", "status": "no_image", "message": "No image provided"}

        if image_file and image_file.filename:
            if not allowed_file(image_file.filename):
                return jsonify({
                    "success": False,
                    "error": f"Invalid image format. Allowed formats: {', '.join(Config.ALLOWED_EXTENSIONS)}"
                }), 400
                
            # Generate collision-free safe filename
            orig_name = secure_filename(image_file.filename)
            extension = orig_name.rsplit(".", 1)[1].lower() if "." in orig_name else "jpg"
            saved_filename = f"{uuid.uuid4().hex[:12]}_{orig_name[:24]}.{extension}"
            image_saved_path = os.path.join(Config.UPLOAD_FOLDER, saved_filename)
            
            image_file.save(image_saved_path)
            logger.info("Uploaded image saved to: %s", image_saved_path)
            
            # Step 1: Image Processing & OCR
            ocr_result = ocr_service.extract_text_from_image(image_saved_path)

        # Validation: At least one of problem text or image must be provided
        if not problem_text and not image_saved_path:
            return jsonify({
                "success": False,
                "error": "Please provide either a description of your problem or upload an image."
            }), 400
            
        # If problem text is empty but image provided, create sensible default prompt
        if not problem_text and image_saved_path:
            problem_text = "Please examine this image, diagnose what is pictured or broken, read any text or error codes, and provide step-by-step guidance."

        # Step 2: AI / LLM Analysis
        ocr_text = ocr_result.get("text", "")
        ai_guidance = ai_service.call_gemini_api(
            problem_text=problem_text,
            category=category,
            urgency=urgency,
            image_path=image_saved_path,
            ocr_text=ocr_text,
            custom_api_key=custom_api_key or None
        )

        if not ai_guidance:
            return jsonify({
                "success": False,
                "error": "Could not generate assistance for this request. Please try again or rephrase."
            }), 500

        # Step 3: Store in database for user history & bookmarking
        record_id = database.save_query(
            problem_text=problem_text,
            category=ai_guidance.get("category", category),
            urgency=urgency,
            image_filename=saved_filename,
            ocr_text=ocr_text,
            ai_response_dict=ai_guidance
        )

        image_url = f"/uploads/{saved_filename}" if saved_filename else None

        return jsonify({
            "success": True,
            "record_id": record_id,
            "data": ai_guidance,
            "ocr": ocr_result,
            "image_url": image_url
        })

    except Exception as e:
        logger.exception("Unexpected error in /api/analyze: %s", str(e))
        return jsonify({
            "success": False,
            "error": f"An error occurred while processing your request: {str(e)}"
        }), 500

@app.route("/api/ocr", methods=["POST"])
def ocr_only():
    """Standalone OCR preview endpoint for extracting text from an image."""
    try:
        image_file = request.files.get("image")
        if not image_file or not image_file.filename:
            return jsonify({"success": False, "error": "No image uploaded"}), 400
            
        if not allowed_file(image_file.filename):
            return jsonify({"success": False, "error": "Invalid image extension"}), 400
            
        orig_name = secure_filename(image_file.filename)
        saved_filename = f"ocr_{uuid.uuid4().hex[:8]}_{orig_name}"
        image_saved_path = os.path.join(Config.UPLOAD_FOLDER, saved_filename)
        image_file.save(image_saved_path)
        
        result = ocr_service.extract_text_from_image(image_saved_path)
        return jsonify({
            "success": True,
            "ocr": result,
            "image_url": f"/uploads/{saved_filename}"
        })
    except Exception as e:
        logger.exception("Error in /api/ocr: %s", str(e))
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/history", methods=["GET"])
def get_history_feed():
    """Retrieve paginated problem history."""
    try:
        limit = min(int(request.args.get("limit", 20)), 100)
        offset = int(request.args.get("offset", 0))
        category = request.args.get("category", None)
        bookmarked_only = request.args.get("bookmarked", "false").lower() in ("true", "1")
        search = request.args.get("search", None)

        history_items = database.get_history(
            limit=limit,
            offset=offset,
            category=category,
            bookmarked_only=bookmarked_only,
            search_term=search
        )
        return jsonify({"success": True, "items": history_items})
    except Exception as e:
        logger.error("Error in /api/history: %s", str(e))
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/history/<int:record_id>", methods=["GET"])
def get_single_history(record_id):
    """Retrieve full details of a past query."""
    record = database.get_query_by_id(record_id)
    if not record:
        return jsonify({"success": False, "error": "Record not found"}), 404
    return jsonify({"success": True, "record": record})

@app.route("/api/history/<int:record_id>/bookmark", methods=["POST"])
def toggle_bookmark_item(record_id):
    """Toggle bookmark for a specific history item."""
    state = database.toggle_bookmark(record_id)
    return jsonify({"success": True, "bookmarked": state})

@app.route("/api/history/<int:record_id>/feedback", methods=["POST"])
def submit_item_feedback(record_id):
    """Submit helpfulness rating (1 or -1) and optional note."""
    data = request.get_json(silent=True) or {}
    rating = int(data.get("rating", 1))
    note = str(data.get("note", ""))[:500]
    success = database.submit_feedback(record_id, rating, note)
    return jsonify({"success": success})

@app.route("/api/history/<int:record_id>", methods=["DELETE"])
def delete_single_history(record_id):
    """Delete a past history record."""
    success = database.delete_query(record_id)
    return jsonify({"success": success})

@app.route("/api/history", methods=["DELETE"])
def clear_all_history():
    """Clear all past history records."""
    success = database.clear_all_history()
    return jsonify({"success": success})

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    """Serve uploaded images securely."""
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        "success": False,
        "error": "The uploaded file exceeds the 16MB file size limit. Please choose a smaller image."
    }), 413

@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Requested resource not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info("Starting HelpLens Server on %s:%s", Config.HOST, Config.PORT)
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
