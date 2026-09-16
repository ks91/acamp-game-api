from flask import Flask, jsonify


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    if config:
        app.config.update(config)

    @app.get("/health")
    def health():
        return jsonify(
            api_version="v1",
            service="acamp-game-api",
            status="ok",
        )

    return app


app = create_app()
