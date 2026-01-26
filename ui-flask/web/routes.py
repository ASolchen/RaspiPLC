from flask import render_template, request, jsonify
import time
import logging
log = logging.getLogger(__name__)

from tags.historian import get_historian


def register_routes(app):

    # -----------------------------
    # Pages
    # -----------------------------

    @app.route("/")
    def index():
        return render_template("pages/index.html")

    @app.route("/temp-chart")
    def temp_chart():
        return render_template("pages/temp_chart.html")

    @app.route("/maintenance")
    def maintenance():
        return render_template("pages/maintenance.html")

    @app.route("/update", methods=["POST"])
    def update_project():
        output = "Updated project...\n"
        return render_template("pages/maintenance.html", output=output)

    @app.route("/api/history", methods=["GET"])
    def api_history():
        tags_param = request.args.get("tags")
        

        if not tags_param:
            return jsonify({"error": "tags are required"}), 400

        try:
            start_param = int(request.args.get("start")) #js Date
            end_param = int(request.args.get("end")) #js Date
            interval = int(request.args.get("interval")) # seconds
            tags = [t.strip() for t in tags_param.split(",") if t.strip()]

        except ValueError:
            return jsonify({"error": "invalid query parameters"}), 400

        # ------------------------------------------------------------
        # Decide query mode
        # ------------------------------------------------------------

        rows = get_historian().query_history(tags, start_param, end_param, interval)

        # ------------------------------------------------------------
        # ALWAYS return a response
        # ------------------------------------------------------------

        return jsonify({
            "rows": rows
        })
