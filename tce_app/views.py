# -*- coding: utf-8 -*-
from flask import Blueprint, jsonify, g
from .auth import auth_required

bp = Blueprint("main", __name__)


@bp.route("/healthz", methods=["GET"])  # unprotected
def healthz():
    return jsonify({"status": "ok"})


@bp.route("/whoami", methods=["GET"])  # protected, any authenticated user
@auth_required()
def whoami():
    return jsonify({"user": g.user.as_dict(), "source": "DASH LTPA"})


@bp.route("/dashboard", methods=["GET"])  # protected, role-gated example
@auth_required(required_roles=["TCE_ADMIN", "NETCOOL_ADMIN"])  # change as needed
def dashboard():
    return jsonify(
        {
            "message": "Welcome to the TCE dashboard",
            "user": g.user.as_dict(),
            "required_roles": ["TCE_ADMIN", "NETCOOL_ADMIN"],
        }
    )
