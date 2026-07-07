from app.models.extension import ExtensionValidationRecord
from app.models.system import (
    ExtensionPackageStatus,
    ProductionReadinessResponse,
    ReadinessCheck,
    StagingValidationCommand,
    StagingValidationResponse,
)


REQUIRED_EXTENSION_SITE_PATTERNS = {
    "linkedin": ("linkedin",),
    "naukri": ("naukri",),
    "indeed": ("indeed",),
    "company_careers": ("career", "greenhouse", "lever", "workday", "company"),
}


def build_staging_validation(
    readiness: ProductionReadinessResponse,
    extension_package: ExtensionPackageStatus,
    extension_validations: list[ExtensionValidationRecord],
    api_base_url: str,
    frontend_url: str,
    user_id: str | None = None,
) -> StagingValidationResponse:
    checks = [
        _environment_check(readiness),
        _readiness_check(readiness),
        _url_check("api_url", "Staging API URL", api_base_url),
        _url_check("frontend_url", "Staging frontend URL", frontend_url),
        _extension_package_check(extension_package),
        *_extension_site_checks(extension_validations),
    ]
    commands = _commands(api_base_url, frontend_url, user_id)
    failed = [check for check in checks if check.status == "fail"]
    warnings = [check for check in checks if check.status == "warn"]
    next_actions = _next_actions(checks)
    return StagingValidationResponse(
        readyForStaging=not failed and len(warnings) <= 2,
        apiBaseUrl=api_base_url,
        frontendUrl=frontend_url,
        checks=checks,
        commands=commands,
        extensionSites=_extension_site_status(extension_validations),
        nextActions=next_actions,
    )


def _environment_check(readiness: ProductionReadinessResponse) -> ReadinessCheck:
    if readiness.environment in {"staging", "production"}:
        return ReadinessCheck(key="environment", label="Environment profile", status="pass", detail=f"ENVIRONMENT is {readiness.environment}.")
    return ReadinessCheck(key="environment", label="Environment profile", status="warn", detail=f"ENVIRONMENT is {readiness.environment}; use staging for hosted validation.")


def _readiness_check(readiness: ProductionReadinessResponse) -> ReadinessCheck:
    failures = len([check for check in readiness.checks if check.status == "fail"])
    warnings = len([check for check in readiness.checks if check.status == "warn"])
    if failures:
        return ReadinessCheck(key="production_readiness", label="Readiness checks", status="fail", detail=f"{failures} blocker(s), {warnings} warning(s).")
    if warnings:
        return ReadinessCheck(key="production_readiness", label="Readiness checks", status="warn", detail=f"No blockers, {warnings} warning(s).")
    return ReadinessCheck(key="production_readiness", label="Readiness checks", status="pass", detail="Production readiness checks have no blockers or warnings.")


def _url_check(key: str, label: str, value: str) -> ReadinessCheck:
    if value.startswith("https://") and "your-domain.com" not in value:
        return ReadinessCheck(key=key, label=label, status="pass", detail=value)
    if value.startswith("http://127.0.0.1") or value.startswith("http://localhost"):
        return ReadinessCheck(key=key, label=label, status="warn", detail=f"{value} is local; replace with hosted staging URL.")
    return ReadinessCheck(key=key, label=label, status="fail", detail=f"{value} is not a valid hosted https staging URL.")


def _extension_package_check(package: ExtensionPackageStatus) -> ReadinessCheck:
    if package.packaged and not package.missingEntries:
        target = package.packagedFor or package.apiBaseUrl or "configured API"
        return ReadinessCheck(key="extension_package", label="Extension package", status="pass", detail=f"Packaged for {target}.")
    return ReadinessCheck(key="extension_package", label="Extension package", status="warn", detail=package.message)


def _extension_site_checks(validations: list[ExtensionValidationRecord]) -> list[ReadinessCheck]:
    statuses = _extension_site_status(validations)
    checks = []
    for site, status in statuses.items():
        label = "Company careers" if site == "company_careers" else site.title()
        checks.append(
            ReadinessCheck(
                key=f"extension_{site}",
                label=f"Extension {label}",
                status="pass" if status == "pass" else "warn",
                detail="Validated on a real job page." if status == "pass" else "Needs real-page validation or manual fallback check.",
            )
        )
    return checks


def _extension_site_status(validations: list[ExtensionValidationRecord]) -> dict[str, str]:
    output = {}
    for site, markers in REQUIRED_EXTENSION_SITE_PATTERNS.items():
        matched = [
            record for record in validations
            if any(marker in f"{record.site} {record.url or ''}".lower() for marker in markers)
        ]
        output[site] = "pass" if any(record.parserRating in {"pass", "partial"} for record in matched) else "missing"
    return output


def _commands(api_base_url: str, frontend_url: str, user_id: str | None) -> list[StagingValidationCommand]:
    user = user_id or "<user-id>"
    return [
        StagingValidationCommand(
            label="Package extension for staging",
            command=f".\\ai-service\\.venv\\Scripts\\python.exe deployment\\package_extension.py --api {api_base_url} --web {frontend_url} --version 0.1.0-staging",
        ),
        StagingValidationCommand(
            label="Run strict staging smoke",
            command=f".\\ai-service\\.venv\\Scripts\\python.exe deployment\\smoke_check.py --api {api_base_url} --frontend {frontend_url} --user-id {user} --session-token <session-token> --check-extension-package --strict-production",
        ),
        StagingValidationCommand(
            label="Run production rehearsal with staging URLs",
            command=f".\\ai-service\\.venv\\Scripts\\python.exe deployment\\production_rehearsal.py --api {api_base_url} --web {frontend_url}",
        ),
    ]


def _next_actions(checks: list[ReadinessCheck]) -> list[str]:
    actions = []
    for check in checks:
        if check.status == "fail":
            actions.append(f"Fix blocker: {check.label} - {check.detail}")
        elif check.status == "warn":
            actions.append(f"Validate: {check.label} - {check.detail}")
    if not actions:
        actions.append("Run strict smoke with a real staging session token, then validate extension pages.")
    return actions[:8]
