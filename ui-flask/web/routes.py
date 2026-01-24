from flask import render_template, request, jsonify
import time

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

    # -----------------------------
    # Historian REST API
    # -----------------------------

    @app.route("/api/history", methods=["GET"])
    def api_history():
        tags_param = request.args.get("tags")
        start_param = request.args.get("start")
        end_param = request.args.get("end")
        limit_param = request.args.get("limit")

        if not tags_param or not start_param:
            return jsonify({"error": "tags and start are required"}), 400

        try:
            tags = [t.strip() for t in tags_param.split(",") if t.strip()]
            start_ts = int(start_param)
            end_ts = int(end_param) if end_param else int(time.time() * 1000)
            limit = int(limit_param) if limit_param else None
        except ValueError:
            return jsonify({"error": "invalid query parameters"}), 400

        rows = get_historian().query_history(
            tags=tags,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=limit
        )

        return jsonify({
            "start": start_ts,
            "end": end_ts,
            "tags": tags,
            "rows": rows
        })
