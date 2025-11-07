# -*- coding: utf-8 -*-
import logging
import os
from flask import Flask, jsonify
from .settings import SETTINGS
from . import views as main


def create_app():
    app = Flask(__name__)
    
    _validate_secret_key()
    
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


def _validate_secret_key():
    """Validate SECRET_KEY is properly configured"""
    weak_keys = ['change-me', 'secret', 'dev', 'test', 'development', 'default']
    
    if not SETTINGS.FLASK_SECRET_KEY:
        raise ValueError(
            "FLASK_SECRET_KEY is not set. Generate a secure key with: "
            "openssl rand -hex 32"
        )
    
    is_debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    if not is_debug:
        if SETTINGS.FLASK_SECRET_KEY in weak_keys:
            raise ValueError(
                f"FLASK_SECRET_KEY is set to a weak default value: '{SETTINGS.FLASK_SECRET_KEY}'. "
                "Generate a secure key with: openssl rand -hex 32"
            )
        
        if len(SETTINGS.FLASK_SECRET_KEY) < 32:
            raise ValueError(
                f"FLASK_SECRET_KEY is too short ({len(SETTINGS.FLASK_SECRET_KEY)} chars). "
                "Use at least 32 characters. Generate with: openssl rand -hex 32"
            )
    else:
        if SETTINGS.FLASK_SECRET_KEY in weak_keys or len(SETTINGS.FLASK_SECRET_KEY) < 32:
            logging.warning(
                "WARNING: Using weak FLASK_SECRET_KEY in debug mode. "
                "This is acceptable for development but NOT for production!"
            )
