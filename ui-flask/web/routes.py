from flask import render_template, request
import subprocess


def register_routes(app):
    @app.route("/")
    def index():
        return render_template("pages/index.html")

    @app.route("/maintenance")
    def maintenance():
        return render_template("pages/maintenance.html")

    @app.route("/update", methods=["POST"])
    def update_project():
        output = "Updated project...\n"
        return render_template("pages/maintenance.html", output=output)
