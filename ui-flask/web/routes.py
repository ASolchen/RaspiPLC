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

    @app.route("/api/history", methods=["GET"])
    def api_history():
        tags_param = request.args.get("tags")
        start_param = request.args.get("start")
        end_param = request.args.get("end")
        after_param = request.args.get("after")
        limit_param = request.args.get("limit")

        if not tags_param:
            return jsonify({"error": "tags are required"}), 400

        try:
            tags = [t.strip() for t in tags_param.split(",") if t.strip()]
            limit = int(limit_param) if limit_param else None

            start_ts = int(start_param) if start_param else None
            end_ts = int(end_param) if end_param else None
            after_ts = int(after_param) if after_param else None

        except ValueError:
            return jsonify({"error": "invalid query parameters"}), 400

        # ------------------------------------------------------------
        # Decide query mode
        # ------------------------------------------------------------

        if after_ts is not None:
            # Cursor-based (explicit)
            rows = get_historian().query_history(
                tags=tags,
                after_ts=after_ts,
                limit=limit
            )

        elif start_ts is not None and end_ts is not None:
            # Time-window (legacy)
            rows = get_historian().query_history(
                tags=tags,
                start_ts=start_ts,
                end_ts=end_ts,
                limit=limit
            )

        else:
            # Default: cursor from beginning
            rows = get_historian().query_history(
                tags=tags,
                after_ts=0,
                limit=limit
            )

        # ------------------------------------------------------------
        # ALWAYS return a response
        # ------------------------------------------------------------

        return jsonify({
            "rows": rows
        })
