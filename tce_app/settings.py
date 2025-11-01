# -*- coding: utf-8 -*-
import os


class Settings(object):
    """Load configuration from environment variables."""

    def __init__(self):
        # DASH servlet connection
        self.DASH_HOST_IP = os.getenv("DASH_HOST_IP", "127.0.0.1")
        self.DASH_HOST_PORT = int(os.getenv("DASH_HOST_PORT", "443"))
        # e.g. "ltpa-integration/validate"
        self.DASH_INTEGRATION_SERVICE = os.getenv(
            "DASH_INTEGRATION_SERVICE", "ltpa-integration/validate"
        )

        # LTPA token naming
        self.LTPA_TOKEN_NAME = os.getenv("LTPA_TOKEN_NAME", "LtpaToken2")

        # TLS options
        self.VERIFY_TLS = os.getenv("VERIFY_TLS", "true").lower() == "true"
        self.CA_BUNDLE_PATH = os.getenv("CA_BUNDLE_PATH", "")

        # HTTP timeouts
        self.TIMEOUT_SECONDS = float(os.getenv("TIMEOUT_SECONDS", "5"))

        # Flask secret key
        self.FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-me")

        # Expected JSON keys from the DASH servlet
        self.USERNAME_KEYS = os.getenv(
            "USERNAME_KEYS",
            "username,user,userName,userid,principal,cn,uid",
        ).split(",")
        self.ROLES_KEYS = os.getenv(
            "ROLES_KEYS", "roles,roleList,groups,groupList,authorities"
        ).split(",")

    @property
    def base_url(self):
        return "https://{host}:{port}".format(
            host=self.DASH_HOST_IP, port=self.DASH_HOST_PORT
        )

    @property
    def servlet_url(self):
        svc = self.DASH_INTEGRATION_SERVICE.lstrip("/")
        return self.base_url + "/" + svc

    @property
    def requests_verify(self):
        if not self.VERIFY_TLS:
            return False
        if self.CA_BUNDLE_PATH and os.path.exists(self.CA_BUNDLE_PATH):
            return self.CA_BUNDLE_PATH
        return True


SETTINGS = Settings()
