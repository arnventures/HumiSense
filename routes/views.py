from flask import Blueprint, render_template

views_bp = Blueprint("views", __name__)

@views_bp.route("/")
def home():
    return render_template("home.html")

@views_bp.route("/config")
def config():
    return render_template("config.html")

@views_bp.route("/logs")
def logs():
    return render_template("logs.html")
