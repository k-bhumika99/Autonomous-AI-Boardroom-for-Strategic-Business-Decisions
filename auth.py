"""Authentication: signup, signin, logout. Flask-session based."""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from database import db
from models import User

auth_bp = Blueprint("auth", __name__)


def login_required(view_fn):
    @wraps(view_fn)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("🔒 Please sign in to continue.", "info")
            return redirect(url_for("auth.signin", next=request.path))

        # The session can outlive the row it points at — a rebuilt or deleted
        # dev database leaves a cookie whose user_id no longer exists. Without
        # this check current_user() returns None and every page 500s.
        if current_user() is None:
            session.clear()
            flash("👋 Your session expired. Please sign in again.", "info")
            return redirect(url_for("auth.signin", next=request.path))

        return view_fn(*args, **kwargs)
    return wrapped


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db.session.get(User, uid)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user() is not None:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("📝 Please fill in all fields.", "error")
            return render_template("signup.html")
        if len(password) < 6:
            flash("🔑 Password must be at least 6 characters.", "error")
            return render_template("signup.html")
        if password != confirm:
            flash("🔁 Passwords do not match.", "error")
            return render_template("signup.html")
        if User.query.filter_by(email=email).first():
            flash("📧 An account with that email already exists.", "error")
            return render_template("signup.html")

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        session["user_name"] = user.name
        flash(f"Welcome aboard, {user.name}! 🎉", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("signup.html")


@auth_bp.route("/signin", methods=["GET", "POST"])
def signin():
    if current_user() is not None:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("⛔ Invalid email or password.", "error")
            return render_template("signin.html")

        session["user_id"] = user.id
        session["user_name"] = user.name
        flash(f"Welcome back, {user.name}! 👋", "success")
        next_url = request.args.get("next")
        return redirect(next_url or url_for("main.dashboard"))

    return render_template("signin.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("👋 You have been signed out. See you soon!", "info")
    return redirect(url_for("main.home"))
