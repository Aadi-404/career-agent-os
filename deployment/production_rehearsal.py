import argparse
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.production.example.yml"
COMPOSE_ENV_EXAMPLE = ROOT / "deployment" / "env" / "compose.production.env.example"
BACKEND_PRODUCTION_ENV_EXAMPLE = ROOT / "deployment" / "env" / "backend.production.env.example"
FRONTEND_PRODUCTION_ENV_EXAMPLE = ROOT / "deployment" / "env" / "frontend.production.env.example"
PACKAGE_SCRIPT = ROOT / "deployment" / "package_extension.py"
REHEARSAL_DIR = ROOT / "deployment" / "releases" / "extension" / "rehearsal"
REHEARSAL_ZIP = ROOT / "deployment" / "releases" / "extension" / "rehearsal-package.zip"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local production deployment rehearsal checks.")
    parser.add_argument("--api", default="https://api.your-domain.com", help="API URL to use while packaging the extension.")
    parser.add_argument("--web", default="https://app.your-domain.com", help="Web app URL to use while packaging the extension.")
    parser.add_argument("--version", default="0.1.0-rehearsal", help="Extension version to use for packaging rehearsal.")
    parser.add_argument(
        "--compose-config",
        action="store_true",
        help="Also run 'docker compose config' against the production compose example.",
    )
    args = parser.parse_args()

    results = [
        check_required_files(),
        check_env_template(
            "compose production env",
            COMPOSE_ENV_EXAMPLE,
            {
                "POSTGRES_DB",
                "POSTGRES_USER",
                "POSTGRES_PASSWORD",
                "FRONTEND_API_BASE_URL",
                "CORS_ALLOW_ORIGINS",
                "ADMIN_USER_IDS",
                "BILLING_WEBHOOK_SECRET",
            },
        ),
        check_env_template(
            "backend production env",
            BACKEND_PRODUCTION_ENV_EXAMPLE,
            {
                "ENVIRONMENT",
                "DATABASE_URL",
                "REQUIRE_USER_AUTH",
                "ADMIN_USER_IDS",
                "BILLING_WEBHOOK_SECRET",
                "BILLING_CHECKOUT_PROVIDER",
                "BILLING_CHECKOUT_URL",
                "CORS_ALLOW_ORIGINS",
                "LLM_MODE",
                "EMBEDDING_PROVIDER",
                "JD_PARSER_MODE",
            },
        ),
        check_env_template("frontend production env", FRONTEND_PRODUCTION_ENV_EXAMPLE, {"VITE_API_BASE_URL"}),
        check_extension_package(args.api, args.web, args.version),
    ]
    if args.compose_config:
        results.append(check_compose_config())

    for result in results:
        prefix = "PASS" if result.ok else "FAIL"
        print(f"[{prefix}] {result.name}: {result.detail}")

    return 1 if any(not result.ok for result in results) else 0


def check_required_files() -> CheckResult:
    required = [
        COMPOSE_FILE,
        COMPOSE_ENV_EXAMPLE,
        BACKEND_PRODUCTION_ENV_EXAMPLE,
        FRONTEND_PRODUCTION_ENV_EXAMPLE,
        PACKAGE_SCRIPT,
        ROOT / "ai-service" / "Dockerfile",
        ROOT / "frontend" / "Dockerfile",
        ROOT / "extension" / "manifest.json",
        ROOT / "extension" / "popup.js",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        return CheckResult("required files", False, f"missing: {', '.join(missing)}")
    return CheckResult("required files", True, f"{len(required)} deployment file(s) present")


def check_env_template(name: str, path: Path, required_keys: set[str]) -> CheckResult:
    if not path.exists():
        return CheckResult(name, False, f"{path.relative_to(ROOT)} is missing")

    values = read_env_template(path)
    missing = sorted(required_keys - set(values))
    if missing:
        return CheckResult(name, False, f"missing key(s): {', '.join(missing)}")

    placeholder_keys = sorted(key for key, value in values.items() if is_placeholder(value))
    if placeholder_keys:
        return CheckResult(name, True, f"{len(values)} key(s), placeholders to replace: {', '.join(placeholder_keys)}")
    return CheckResult(name, True, f"{len(values)} key(s), no obvious placeholders")


def read_env_template(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in ("replace-with", "your-domain.com", "your-provider.com", "user:password@host"))


def check_extension_package(api_url: str, web_url: str, version: str) -> CheckResult:
    command = [
        sys.executable,
        str(PACKAGE_SCRIPT),
        "--api",
        api_url,
        "--web",
        web_url,
        "--version",
        version,
        "--output",
        str(REHEARSAL_ZIP),
    ]
    try:
        completed = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
        if not REHEARSAL_ZIP.exists():
            return CheckResult("extension package rehearsal", False, "package script completed but zip was not created")
        with zipfile.ZipFile(REHEARSAL_ZIP) as archive:
            names = set(archive.namelist())
        required_entries = {"manifest.json", "config.js", "popup.html", "popup.js", "release.json"}
        missing_entries = sorted(required_entries - names)
        if missing_entries:
            return CheckResult("extension package rehearsal", False, f"zip missing: {', '.join(missing_entries)}")
    except subprocess.CalledProcessError as exc:
        return CheckResult("extension package rehearsal", False, (exc.stderr or exc.stdout or str(exc)).strip())
    except zipfile.BadZipFile as exc:
        return CheckResult("extension package rehearsal", False, f"invalid zip: {exc}")
    finally:
        cleanup_rehearsal_artifacts()

    first_line = completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else "package created"
    return CheckResult("extension package rehearsal", True, first_line)


def cleanup_rehearsal_artifacts() -> None:
    if REHEARSAL_ZIP.exists():
        REHEARSAL_ZIP.unlink()
    if REHEARSAL_DIR.exists():
        shutil.rmtree(REHEARSAL_DIR)
    parent = REHEARSAL_ZIP.parent
    try:
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
    except OSError:
        pass


def check_compose_config() -> CheckResult:
    command = ["docker", "compose", "--env-file", str(COMPOSE_ENV_EXAMPLE), "-f", str(COMPOSE_FILE), "config"]
    try:
        completed = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        return CheckResult("docker compose config", False, "docker command not found")
    except subprocess.CalledProcessError as exc:
        return CheckResult("docker compose config", False, (exc.stderr or exc.stdout or str(exc)).strip())

    services = [line.strip() for line in completed.stdout.splitlines() if line.startswith("  ") and line.strip().endswith(":")]
    return CheckResult("docker compose config", True, f"compose config rendered ({len(services)} service-like block(s))")


if __name__ == "__main__":
    sys.exit(main())
