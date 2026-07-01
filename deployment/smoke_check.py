import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deployment smoke checks for Career Agent OS.")
    parser.add_argument("--api", default="http://localhost:8000", help="Backend API base URL.")
    parser.add_argument("--frontend", default="", help="Frontend URL to check.")
    parser.add_argument("--session-token", default="", help="Optional X-Session-Token for guarded diagnostics.")
    parser.add_argument("--user-id", default="", help="Optional user id for user-scoped diagnostics.")
    parser.add_argument("--strict-production", action="store_true", help="Fail when production readiness has warnings.")
    args = parser.parse_args()

    api_base = args.api.rstrip("/")
    results = [
        check_json("backend health", f"{api_base}/health", args.session_token, expected_status="ok"),
        check_json("backend ready", f"{api_base}/ready", args.session_token, expected_status="ready"),
        check_readiness(api_base, args.user_id, args.session_token, args.strict_production),
    ]
    if args.frontend:
        results.append(check_page("frontend", args.frontend.rstrip("/")))

    for result in results:
        prefix = "PASS" if result.ok else "FAIL"
        print(f"[{prefix}] {result.name}: {result.detail}")

    failed = [result for result in results if not result.ok]
    return 1 if failed else 0


def check_json(name: str, url: str, session_token: str, expected_status: str) -> CheckResult:
    try:
        payload = request_json(url, session_token)
    except Exception as exc:
        return CheckResult(name, False, str(exc))

    actual_status = str(payload.get("status", ""))
    if actual_status != expected_status:
        return CheckResult(name, False, f"expected status={expected_status}, received status={actual_status or 'missing'}")
    return CheckResult(name, True, f"status={actual_status}")


def check_readiness(api_base: str, user_id: str, session_token: str, strict_production: bool) -> CheckResult:
    url = f"{api_base}/diagnostics/production-readiness"
    if user_id:
        url = f"{url}?userId={user_id}"
    try:
        payload = request_json(url, session_token)
    except Exception as exc:
        return CheckResult("production readiness", False, str(exc))

    failed_checks = [check for check in payload.get("checks", []) if check.get("status") == "fail"]
    warned_checks = [check for check in payload.get("checks", []) if check.get("status") == "warn"]
    if failed_checks:
        return CheckResult("production readiness", False, summarize_checks("failed", failed_checks))
    if strict_production and warned_checks:
        return CheckResult("production readiness", False, summarize_checks("warning", warned_checks))
    if warned_checks:
        return CheckResult("production readiness", True, summarize_checks("warning", warned_checks))
    return CheckResult("production readiness", True, "no failed or warning checks")


def check_page(name: str, url: str) -> CheckResult:
    try:
        with urlopen(Request(url, headers={"User-Agent": "career-agent-os-smoke-check"}), timeout=15) as response:
            status = response.status
    except HTTPError as exc:
        return CheckResult(name, False, f"HTTP {exc.code}")
    except URLError as exc:
        return CheckResult(name, False, str(exc.reason))
    except TimeoutError:
        return CheckResult(name, False, "request timed out")

    if status >= 400:
        return CheckResult(name, False, f"HTTP {status}")
    return CheckResult(name, True, f"HTTP {status}")


def request_json(url: str, session_token: str) -> dict[str, Any]:
    headers = {"Accept": "application/json", "User-Agent": "career-agent-os-smoke-check"}
    if session_token:
        headers["X-Session-Token"] = session_token
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc
    except TimeoutError as exc:
        raise RuntimeError("request timed out") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON response from {url}: {exc}") from exc


def summarize_checks(label: str, checks: list[dict[str, Any]]) -> str:
    names = ", ".join(str(check.get("label") or check.get("key")) for check in checks)
    return f"{len(checks)} {label} check(s): {names}"


if __name__ == "__main__":
    sys.exit(main())
