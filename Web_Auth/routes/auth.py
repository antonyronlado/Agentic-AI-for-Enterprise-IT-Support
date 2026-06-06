from flask import (
    Blueprint, render_template, request,
    redirect, url_for, current_app, flash, jsonify
)
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity,
    set_access_cookies, unset_jwt_cookies
)
from models.user import UserModel, check_password

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    return render_template("index.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    confirm  = request.form.get("confirm_password", "").strip()

    if not name or not email or not password:
        return render_template("register.html", error="All fields are required.")

    if len(password) < 6:
        return render_template("register.html", error="Password must be at least 6 characters.", name=name, email=email)

    if password != confirm:
        return render_template("register.html", error="Passwords do not match.", name=name, email=email)

    users = UserModel(current_app.db)

    if users.email_exists(email):
        return render_template("register.html", error="This email is already registered. Please login.", name=name)

    users.create(name, email, password)
    return redirect(url_for("auth.index") + "?registered=true")


@auth_bp.route("/login", methods=["POST"])
def login():
    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not email or not password:
        return render_template("index.html", error="Email and password are required.")

    users = UserModel(current_app.db)
    user  = users.find_by_email(email)

    if not user or not check_password(password, user["password_hash"]):
        return render_template("index.html", error="Invalid email or password. Please try again.")

    token    = create_access_token(identity=email)
    response = redirect(url_for("auth.dashboard"))
    set_access_cookies(response, token)
    return response


@auth_bp.route("/dashboard")
@jwt_required()
def dashboard():
    email = get_jwt_identity()
    users = UserModel(current_app.db)
    user  = users.find_by_email(email)
    if not user:
        response = redirect(url_for("auth.index"))
        unset_jwt_cookies(response)
        return response
    return render_template("dashboard.html", user=user)


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    email       = get_jwt_identity()
    new_pw      = request.form.get("new_password", "").strip()
    confirm_pw  = request.form.get("confirm_password", "").strip()

    users = UserModel(current_app.db)
    user  = users.find_by_email(email)

    if not user:
        response = redirect(url_for("auth.index"))
        unset_jwt_cookies(response)
        return response

    if not new_pw or len(new_pw) < 8:
        return render_template("dashboard.html", user=user,
                               pw_error="New password must be at least 8 characters.")

    if new_pw != confirm_pw:
        return render_template("dashboard.html", user=user,
                               pw_error="Passwords do not match. Please try again.")

    users.update_password(email, new_pw, temp=False)

    return redirect(url_for("auth.dashboard") + "?pw_changed=true")


@auth_bp.route("/logout")
def logout():
    response = redirect(url_for("auth.index") + "?logged_out=true")
    unset_jwt_cookies(response)
    return response
