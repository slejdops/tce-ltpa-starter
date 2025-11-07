# -*- coding: utf-8 -*-
from flask import Blueprint, jsonify, g, request
from .auth import auth_required
from .diagnostics import DiagnosticRunner

bp = Blueprint("main", __name__)

# Initialize diagnostic runner
diagnostic_runner = DiagnosticRunner()


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


# Diagnostic Endpoints

@bp.route("/diagnostics/health", methods=["GET"])
def diagnostics_health():
    """Quick health check endpoint (unprotected for monitoring)"""
    runner = DiagnosticRunner()
    status = runner.get_health_status()
    http_code = 200 if status['healthy'] else 503
    return jsonify(status), http_code


@bp.route("/diagnostics/check-all", methods=["GET"])
@auth_required(required_roles=["TCE_ADMIN", "NETCOOL_ADMIN"])
def diagnostics_check_all():
    """Run all diagnostic checks"""
    runner = DiagnosticRunner()
    quick = request.args.get('quick', 'false').lower() == 'true'
    results = runner.run_all_checks(quick=quick)
    return jsonify(results)


@bp.route("/diagnostics/check-ltpa", methods=["GET"])
@auth_required(required_roles=["TCE_ADMIN", "NETCOOL_ADMIN"])
def diagnostics_check_ltpa():
    """Run LTPA diagnostics only"""
    runner = DiagnosticRunner()
    results = runner.run_ltpa_checks()
    return jsonify(results)


@bp.route("/diagnostics/check-session", methods=["GET"])
@auth_required(required_roles=["TCE_ADMIN", "NETCOOL_ADMIN"])
def diagnostics_check_session():
    """Run session diagnostics only"""
    runner = DiagnosticRunner()
    results = runner.run_session_checks()
    return jsonify(results)


@bp.route("/diagnostics/check-performance", methods=["GET"])
@auth_required(required_roles=["TCE_ADMIN", "NETCOOL_ADMIN"])
def diagnostics_check_performance():
    """Run performance diagnostics only"""
    runner = DiagnosticRunner()
    results = runner.run_performance_checks()
    return jsonify(results)


@bp.route("/diagnostics/validate-token", methods=["POST"])
@auth_required(required_roles=["TCE_ADMIN", "NETCOOL_ADMIN"])
def diagnostics_validate_token():
    """Validate a specific LTPA token"""
    runner = DiagnosticRunner()
    data = request.get_json() or {}
    token = data.get('token') or request.cookies.get('LtpaToken2')

    if not token:
        return jsonify({"error": "No token provided"}), 400

    results = runner.validate_token(token)
    http_code = 200 if results.get('valid') else 401
    return jsonify(results), http_code


@bp.route("/diagnostics/test-session", methods=["POST"])
@auth_required(required_roles=["TCE_ADMIN", "NETCOOL_ADMIN"])
def diagnostics_test_session():
    """Test session persistence"""
    runner = DiagnosticRunner()
    data = request.get_json() or {}
    test_url = data.get('url')
    token = data.get('token')
    num_requests = data.get('num_requests', 5)

    if not test_url or not token:
        return jsonify({"error": "url and token are required"}), 400

    from .security import validate_url
    if not validate_url(test_url):
        return jsonify({"error": "Invalid or disallowed URL"}), 400

    results = runner.test_session_persistence(
        test_url, token, num_requests
    )
    return jsonify(results)


@bp.route("/diagnostics/benchmark", methods=["POST"])
@auth_required(required_roles=["TCE_ADMIN", "NETCOOL_ADMIN"])
def diagnostics_benchmark():
    """Benchmark an endpoint"""
    runner = DiagnosticRunner()
    data = request.get_json() or {}
    url = data.get('url')
    num_requests = data.get('num_requests', 10)
    token = data.get('token')

    if not url:
        return jsonify({"error": "url is required"}), 400

    from .security import validate_url
    if not validate_url(url):
        return jsonify({"error": "Invalid or disallowed URL"}), 400

    results = runner.benchmark_endpoint(url, num_requests, token)
    return jsonify(results)


@bp.route("/diagnostics/search-logs", methods=["GET"])
@auth_required(required_roles=["TCE_ADMIN", "NETCOOL_ADMIN"])
def diagnostics_search_logs():
    """Search logs for errors"""
    runner = DiagnosticRunner()
    max_matches = request.args.get('max_matches', 100, type=int)

    # Parse search_dirs and exclude_dirs from query params
    search_dirs = None
    if request.args.get('dirs'):
        search_dirs = request.args.get('dirs').split(',')
        from .security import validate_log_directories
        search_dirs = validate_log_directories(search_dirs)

    exclude_dirs = None
    if request.args.get('exclude_dirs'):
        exclude_dirs = request.args.get('exclude_dirs').split(',')

    results = runner.search_logs(
        search_dirs=search_dirs,
        exclude_dirs=exclude_dirs,
        max_matches=max_matches
    )
    return jsonify({"matches": results, "count": len(results)})


@bp.route("/diagnostics/report", methods=["GET"])
@auth_required(required_roles=["TCE_ADMIN", "NETCOOL_ADMIN"])
def diagnostics_report():
    """Generate comprehensive diagnostic report"""
    runner = DiagnosticRunner()
    include_logs = request.args.get('include_logs', 'false').lower() == 'true'
    report = runner.generate_report(include_logs=include_logs)
    return jsonify(report)
