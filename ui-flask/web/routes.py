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
        repo_dir = "/home/engineer/RaspiPLC"
        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout + result.stderr
        except Exception as e:
            output = str(e)

        return render_template("pages/maintenance.html", output=output)
