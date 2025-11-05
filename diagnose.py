#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Netcool DASH/JazzSM/WebGUI Diagnostic Tool

Command-line interface for diagnosing LTPA token, session, and performance issues.
"""

import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from tce_app.diagnostics import DiagnosticRunner
from tce_app.diagnostics.base import DiagnosticLevel


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def print_results(results, format='text', output_file=None):
    """Print diagnostic results in specified format"""
    if format == 'json':
        output = json.dumps(results, indent=2)
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            print(f"Results written to {output_file}")
        else:
            print(output)
    else:
        # Text format
        print_text_results(results)
        if output_file:
            with open(output_file, 'w') as f:
                f.write(format_text_results(results))
            print(f"\nResults written to {output_file}")


def print_text_results(results):
    """Print results in human-readable text format"""
    print("\n" + "="*80)
    print("NETCOOL DASH/JazzSM/WebGUI DIAGNOSTIC REPORT")
    print("="*80)
    print(f"Generated: {results.get('started_at', 'unknown')}")
    print(f"Duration: {results.get('duration_seconds', 0):.2f} seconds")
    print(f"Overall Status: {results.get('overall_status', 'unknown').upper()}")
    print("="*80)

    # Print summary
    summary = results.get('summary', {})
    if summary:
        print("\n" + "-"*80)
        print("SUMMARY")
        print("-"*80)
        for category, counts in summary.items():
            print(f"\n{category.upper()}:")
            for level, count in counts.items():
                if count > 0:
                    symbol = get_level_symbol(level)
                    print(f"  {symbol} {level.capitalize()}: {count}")

    # Print detailed checks
    checks = results.get('checks', {})
    for category, check_list in checks.items():
        if isinstance(check_list, list) and check_list:
            print("\n" + "-"*80)
            print(f"{category.upper()} CHECKS")
            print("-"*80)

            for check in check_list:
                level = check.get('level', 'info')
                name = check.get('name', 'Unknown')
                message = check.get('message', '')
                recommendation = check.get('recommendation')

                symbol = get_level_symbol(level)
                print(f"\n{symbol} {name}")
                print(f"  {message}")

                if recommendation:
                    print(f"  → Recommendation: {recommendation}")

                details = check.get('details')
                if details and isinstance(details, dict):
                    print(f"  Details: {json.dumps(details, indent=4)}")

    # Print recommendations
    recommendations = results.get('recommendations', [])
    if recommendations:
        print("\n" + "-"*80)
        print("RECOMMENDATIONS")
        print("-"*80)
        for rec in recommendations:
            priority = rec.get('priority', 'info')
            symbol = get_level_symbol(priority)
            print(f"\n{symbol} [{rec.get('category', 'general')}] {rec.get('message')}")

    print("\n" + "="*80)


def format_text_results(results):
    """Format results as text for file output"""
    lines = []
    lines.append("="*80)
    lines.append("NETCOOL DASH/JazzSM/WebGUI DIAGNOSTIC REPORT")
    lines.append("="*80)
    lines.append(f"Generated: {results.get('started_at', 'unknown')}")
    lines.append(f"Overall Status: {results.get('overall_status', 'unknown').upper()}")
    lines.append("")

    for category, check_list in results.get('checks', {}).items():
        if isinstance(check_list, list):
            lines.append(f"\n{category.upper()} CHECKS")
            lines.append("-"*80)
            for check in check_list:
                lines.append(f"{check.get('name')}: {check.get('message')}")
                if check.get('recommendation'):
                    lines.append(f"  → {check.get('recommendation')}")

    return "\n".join(lines)


def get_level_symbol(level):
    """Get symbol for diagnostic level"""
    symbols = {
        'success': '✓',
        'info': 'ℹ',
        'warning': '⚠',
        'error': '✗',
        'critical': '⚠⚠',
    }
    return symbols.get(level.lower(), '•')


def cmd_check_all(args):
    """Run all diagnostic checks"""
    runner = DiagnosticRunner()
    results = runner.run_all_checks(quick=args.quick)

    if args.include_logs:
        results['log_analysis'] = {
            'errors': runner.search_logs(max_matches=args.max_log_matches)
        }

    print_results(results, format=args.format, output_file=args.output)

    # Return exit code based on status
    status = results.get('overall_status', 'unknown')
    if status == 'critical':
        return 2
    elif status == 'error':
        return 1
    else:
        return 0


def cmd_check_ltpa(args):
    """Run LTPA diagnostics only"""
    runner = DiagnosticRunner()
    results = runner.run_ltpa_checks()
    print_results(results, format=args.format, output_file=args.output)
    return 0


def cmd_check_session(args):
    """Run session diagnostics only"""
    runner = DiagnosticRunner()
    results = runner.run_session_checks()
    print_results(results, format=args.format, output_file=args.output)
    return 0


def cmd_check_performance(args):
    """Run performance diagnostics only"""
    runner = DiagnosticRunner()
    results = runner.run_performance_checks()
    print_results(results, format=args.format, output_file=args.output)
    return 0


def cmd_validate_token(args):
    """Validate a specific LTPA token"""
    runner = DiagnosticRunner()
    results = runner.validate_token(args.token)

    print("\n" + "="*80)
    print("LTPA TOKEN VALIDATION")
    print("="*80)
    print(f"Valid: {results.get('valid', False)}")
    print("\nChecks:")
    for check in results.get('checks', []):
        symbol = '✓' if check.get('passed') else '✗'
        print(f"  {symbol} {check.get('name')}: {check.get('message')}")

    if results.get('details'):
        print(f"\nDetails: {json.dumps(results['details'], indent=2)}")

    return 0 if results.get('valid') else 1


def cmd_test_session(args):
    """Test session persistence"""
    runner = DiagnosticRunner()
    results = runner.test_session_persistence(
        args.url,
        args.token,
        num_requests=args.requests
    )

    print("\n" + "="*80)
    print("SESSION PERSISTENCE TEST")
    print("="*80)
    print(f"URL: {args.url}")
    print(f"Total Requests: {results['total_requests']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"Session Stable: {results['session_stable']}")

    if results.get('average_response_time'):
        print(f"\nAverage Response Time: {results['average_response_time']:.2f}ms")
        print(f"Min: {results.get('min_response_time', 0):.2f}ms")
        print(f"Max: {results.get('max_response_time', 0):.2f}ms")

    if args.verbose:
        print("\nDetailed Results:")
        print(json.dumps(results, indent=2))

    return 0 if results['session_stable'] else 1


def cmd_benchmark(args):
    """Benchmark an endpoint"""
    runner = DiagnosticRunner()
    results = runner.benchmark_endpoint(
        args.url,
        num_requests=args.requests,
        ltpa_token=args.token
    )

    print("\n" + "="*80)
    print("ENDPOINT BENCHMARK")
    print("="*80)
    print(f"URL: {args.url}")
    print(f"Total Requests: {results['total_requests']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")

    stats = results.get('statistics', {})
    if stats:
        print(f"\nResponse Time Statistics:")
        print(f"  Mean: {stats.get('mean_ms', 0):.2f}ms")
        print(f"  Median: {stats.get('median_ms', 0):.2f}ms")
        print(f"  Min: {stats.get('min_ms', 0):.2f}ms")
        print(f"  Max: {stats.get('max_ms', 0):.2f}ms")
        print(f"  Std Dev: {stats.get('stddev_ms', 0):.2f}ms")
        print(f"  95th percentile: {stats.get('p95_ms', 0):.2f}ms")
        print(f"  99th percentile: {stats.get('p99_ms', 0):.2f}ms")

    return 0


def cmd_search_logs(args):
    """Search logs for errors"""
    runner = DiagnosticRunner()
    results = runner.search_logs(
        search_dirs=args.dirs.split(',') if args.dirs else None,
        max_matches=args.max_matches
    )

    print("\n" + "="*80)
    print("LOG ERROR SEARCH")
    print("="*80)
    print(f"Found {len(results)} error matches\n")

    for match in results:
        print(f"File: {match['file']}:{match['line_number']}")
        print(f"  {match['content']}")
        print()

    return 0


def cmd_health(args):
    """Quick health check"""
    runner = DiagnosticRunner()
    status = runner.get_health_status()

    print("\n" + "="*80)
    print("HEALTH STATUS")
    print("="*80)
    print(f"Healthy: {status['healthy']}")
    print(f"Timestamp: {status['timestamp']}")
    print("\nChecks:")
    for check_name, check_result in status.get('checks', {}).items():
        if check_name.endswith('_error'):
            continue
        symbol = '✓' if check_result else '✗'
        print(f"  {symbol} {check_name}: {check_result}")
        error_key = f"{check_name}_error"
        if error_key in status['checks']:
            print(f"    Error: {status['checks'][error_key]}")

    return 0 if status['healthy'] else 1


def cmd_report(args):
    """Generate comprehensive report"""
    runner = DiagnosticRunner()
    report = runner.generate_report(include_logs=args.include_logs)

    print_results(report, format=args.format, output_file=args.output)

    status = report.get('overall_status', 'unknown')
    if status == 'critical':
        return 2
    elif status == 'error':
        return 1
    else:
        return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Netcool DASH/JazzSM/WebGUI Diagnostic Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('-o', '--output', help='Output file path')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # check-all command
    p = subparsers.add_parser('check-all', help='Run all diagnostic checks')
    p.add_argument('--quick', action='store_true',
                   help='Skip time-consuming checks')
    p.add_argument('--include-logs', action='store_true',
                   help='Include log analysis')
    p.add_argument('--max-log-matches', type=int, default=50,
                   help='Maximum log error matches to include')
    p.set_defaults(func=cmd_check_all)

    # check-ltpa command
    p = subparsers.add_parser('check-ltpa', help='Run LTPA diagnostics only')
    p.set_defaults(func=cmd_check_ltpa)

    # check-session command
    p = subparsers.add_parser('check-session', help='Run session diagnostics only')
    p.set_defaults(func=cmd_check_session)

    # check-performance command
    p = subparsers.add_parser('check-performance', help='Run performance diagnostics only')
    p.set_defaults(func=cmd_check_performance)

    # validate-token command
    p = subparsers.add_parser('validate-token', help='Validate a specific LTPA token')
    p.add_argument('token', help='LTPA token to validate')
    p.set_defaults(func=cmd_validate_token)

    # test-session command
    p = subparsers.add_parser('test-session', help='Test session persistence')
    p.add_argument('url', help='URL to test')
    p.add_argument('token', help='LTPA token to use')
    p.add_argument('-n', '--requests', type=int, default=5,
                   help='Number of requests (default: 5)')
    p.set_defaults(func=cmd_test_session)

    # benchmark command
    p = subparsers.add_parser('benchmark', help='Benchmark an endpoint')
    p.add_argument('url', help='URL to benchmark')
    p.add_argument('-n', '--requests', type=int, default=10,
                   help='Number of requests (default: 10)')
    p.add_argument('-t', '--token', help='LTPA token (optional)')
    p.set_defaults(func=cmd_benchmark)

    # search-logs command
    p = subparsers.add_parser('search-logs', help='Search logs for errors')
    p.add_argument('--dirs', help='Comma-separated list of directories to search')
    p.add_argument('--max-matches', type=int, default=100,
                   help='Maximum matches to return (default: 100)')
    p.set_defaults(func=cmd_search_logs)

    # health command
    p = subparsers.add_parser('health', help='Quick health check')
    p.set_defaults(func=cmd_health)

    # report command
    p = subparsers.add_parser('report', help='Generate comprehensive diagnostic report')
    p.add_argument('--include-logs', action='store_true',
                   help='Include log analysis in report')
    p.set_defaults(func=cmd_report)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    setup_logging(args.verbose)

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        logging.exception("Error running diagnostic")
        print(f"\nError: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
