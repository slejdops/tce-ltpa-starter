# -*- coding: utf-8 -*-
import logging
from flask import Flask, jsonify
from .settings import SETTINGS
from . import views as main


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SETTINGS.FLASK_SECRET_KEY

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    app.register_blueprint(main.bp)

    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(502)
    @app.errorhandler(500)
    def json_error(err):
        code = getattr(err, "code", 500)
        desc = getattr(err, "description", str(err))
        return jsonify({"error": desc, "status": code}), code

    return app
