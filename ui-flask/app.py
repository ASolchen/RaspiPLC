from flask import Flask
from flask_socketio import SocketIO

from web.routes import register_routes
from tags.runtime import register_tag_namespace

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"

socketio = SocketIO(app, async_mode="threading")

register_routes(app)
register_tag_namespace(socketio)

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        allow_unsafe_werkzeug=True,
    )

