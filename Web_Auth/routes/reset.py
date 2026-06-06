import secrets
import string
from flask import Blueprint, request, jsonify, current_app
from models.user import UserModel

reset_bp = Blueprint("reset", __name__, url_prefix="/api")

_TEMP_PW_LENGTH = 12

def _generate_temp_password(length: int = _TEMP_PW_LENGTH) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def _validate_api_key(req) -> bool:
    api_key = req.headers.get("X-API-Key", "") or (req.get_json(silent=True) or {}).get("api_key", "")
    return api_key == current_app.config["RESET_API_KEY"]

@reset_bp.route("/reset-password", methods=["POST"])
def reset_password():
    if not _validate_api_key(request):
        return jsonify({"success": False, "error": "Unauthorized — invalid API key"}), 401

    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"success": False, "error": "Email is required"}), 400

    users = UserModel(current_app.db)
    user = users.find_by_email(email)

    if not user:
        return jsonify({"success": False, "error": f"No account found for email: {email}"}), 404

    temp_password = _generate_temp_password()
    success = users.update_password(email, temp_password, temp=True)

    if not success:
        return jsonify({"success": False, "error": "Password reset failed — please try again"}), 500

    return jsonify({
        "success": True,
        "message": f"Password reset successful for {email}",
        "email": email,
        "name": user.get("name", "User"),
        "temp_password": temp_password,
        "note": "This is a one-time temporary password. The user must change it on next login.",
        "website": current_app.config.get("WEBSITE_NAME", "Web_Auth"),
    }), 200

@reset_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "online",
        "website": current_app.config.get("WEBSITE_NAME", "Web_Auth"),
        "reset_endpoint": "/api/reset-password",
    }), 200