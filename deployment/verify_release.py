import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AI_SERVICE_DIR = ROOT / "ai-service"
FRONTEND_DIR = ROOT / "frontend"
PYTHON_EXE = AI_SERVICE_DIR / ".venv" / "Scripts" / "python.exe"


@dataclass
class Check:
    name: str
    command: list[str]
    cwd: Path = ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Career Agent OS release verification checks.")
    parser.add_argument("--skip-frontend-build", action="store_true", help="Skip npm run build.")
    parser.add_argument("--skip-backend-tests", action="store_true", help="Skip backend unittest suite.")
    parser.add_argument("--skip-rehearsal", action="store_true", help="Skip production rehearsal.")
    parser.add_argument("--api", default="http://127.0.0.1:8001", help="API URL used for production rehearsal.")
    parser.add_argument("--web", default="http://127.0.0.1:8080", help="Web URL used for production rehearsal.")
    args = parser.parse_args()

    python = str(resolve_python())
    node = resolve_tool("node")
    npm = resolve_tool("npm")
    checks: list[Check] = []
    if not args.skip_backend_tests:
        checks.append(Check("backend tests", [python, "-m", "unittest", "discover", "-s", "tests"], AI_SERVICE_DIR))
    checks.extend(
        [
            Check("backend compile", [python, "-m", "compileall", "app"], AI_SERVICE_DIR),
            Check(
                "deployment script compile",
                [
                    python,
                    "-m",
                    "py_compile",
                    "deployment/smoke_check.py",
                    "deployment/package_extension.py",
                    "deployment/backup_database.py",
                    "deployment/restore_database.py",
                    "deployment/production_rehearsal.py",
                    "deployment/seed_demo_data.py",
                    "deployment/verify_release.py",
                ],
            ),
            Check("extension popup syntax", [node, "--check", "extension/popup.js"]),
            Check("extension parser fixtures", [node, "extension/test-content-script.mjs"]),
        ]
    )
    if not args.skip_frontend_build:
        checks.append(Check("frontend build", [npm, "run", "build"], FRONTEND_DIR))
    checks.append(Check("frontend smoke", [npm, "run", "smoke"], FRONTEND_DIR))
    if not args.skip_rehearsal:
        checks.append(Check("production rehearsal", [python, "deployment/production_rehearsal.py", "--api", args.api, "--web", args.web]))

    failures: list[str] = []
    for check in checks:
        print(f"\n==> {check.name}")
        completed = subprocess.run(check.command, cwd=check.cwd, text=True)
        if completed.returncode:
            failures.append(check.name)
            break

    if failures:
        print(f"\nRelease verification failed at: {', '.join(failures)}")
        return 1

    print(f"\nRelease verification passed ({len(checks)} checks).")
    return 0


def resolve_python() -> Path:
    if PYTHON_EXE.exists():
        return PYTHON_EXE
    executable = shutil.which("python") or shutil.which("py")
    if executable:
        return Path(executable)
    raise SystemExit("Python was not found. Create ai-service/.venv or install Python on PATH.")


def resolve_tool(name: str) -> str:
    executable = shutil.which(name)
    if executable:
        return executable
    raise SystemExit(f"{name} was not found on PATH.")


if __name__ == "__main__":
    sys.exit(main())
