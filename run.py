#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from tce_app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.logger.info("Starting app on %s:%s (debug=%s)", host, port, debug)
    app.run(host=host, port=port, debug=debug)
