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
    parser.add_argument("--billing-webhook-secret", default="", help="Optional billing webhook secret for subscription webhook smoke checks.")
    parser.add_argument("--billing-user-id", default="", help="Optional user id to use for billing webhook smoke checks. Defaults to --user-id when omitted.")
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
    if args.user_id:
        results.append(check_comparison_history(api_base, args.user_id, args.session_token))
    billing_user_id = args.billing_user_id or args.user_id
    if args.billing_webhook_secret and billing_user_id:
        results.append(check_billing_webhook(api_base, billing_user_id, args.billing_webhook_secret))

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


def check_comparison_history(api_base: str, user_id: str, session_token: str) -> CheckResult:
    try:
        payload = request_json(f"{api_base}/history/users/{user_id}/comparisons", session_token)
    except Exception as exc:
        return CheckResult("comparison history API", False, str(exc))
    if not isinstance(payload, list):
        return CheckResult("comparison history API", False, "expected a JSON list")
    return CheckResult("comparison history API", True, f"{len(payload)} saved comparison run(s)")


def check_billing_webhook(api_base: str, user_id: str, billing_webhook_secret: str) -> CheckResult:
    payload = {
        "provider": "stripe",
        "providerPayload": {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "smoke_sub_check",
                    "customer": "smoke_customer_check",
                    "status": "active",
                    "metadata": {"userId": user_id},
                    "items": {"data": [{"price": {"id": "smoke_plan_check"}}]},
                }
            },
        },
    }
    try:
        response = request_json(
            f"{api_base}/billing/webhooks/subscription",
            session_token="",
            method="POST",
            body=payload,
            extra_headers={"X-Billing-Webhook-Secret": billing_webhook_secret},
        )
    except Exception as exc:
        return CheckResult("billing webhook API", False, str(exc))

    if response.get("id") != user_id:
        return CheckResult("billing webhook API", False, f"expected user {user_id}, got {response.get('id') or 'missing'}")
    if response.get("subscriptionStatus") != "active":
        return CheckResult("billing webhook API", False, f"expected active status, got {response.get('subscriptionStatus') or 'missing'}")
    if response.get("subscriptionPlanId") != "smoke_plan_check":
        return CheckResult("billing webhook API", False, "provider plan id was not mapped")
    return CheckResult("billing webhook API", True, "stripe-shaped webhook mapped and accepted")


def request_json(
    url: str,
    session_token: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> Any:
    headers = {"Accept": "application/json", "User-Agent": "career-agent-os-smoke-check"}
    if session_token:
        headers["X-Session-Token"] = session_token
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    request = Request(url, data=data, headers=headers, method=method)
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
