import argparse
import json
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
EXTENSION_DIR = ROOT / "extension"
RELEASE_DIR = ROOT / "deployment" / "releases" / "extension"


def main() -> int:
    parser = argparse.ArgumentParser(description="Package the Career Agent OS browser extension.")
    parser.add_argument("--api", required=True, help="Backend API base URL the extension should call.")
    parser.add_argument("--web", default="http://127.0.0.1:5173", help="Web app URL opened from extension history links.")
    parser.add_argument("--version", default="", help="Optional manifest version override.")
    parser.add_argument("--output", default="", help="Optional output zip path.")
    args = parser.parse_args()

    api_base = normalize_api_base(args.api)
    web_base = normalize_web_base(args.web)
    output_dir = RELEASE_DIR / safe_release_name(api_base, args.version)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    copy_extension_files(output_dir)
    manifest = update_manifest(output_dir / "manifest.json", api_base, args.version)
    write_config(output_dir / "config.js", api_base, web_base)
    zip_path = Path(args.output) if args.output else Path(f"{output_dir}.zip")
    if zip_path.exists():
        zip_path.unlink()
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    write_release_metadata(output_dir / "release.json", manifest["version"], api_base, web_base, output_dir, zip_path)
    create_zip(output_dir, zip_path)

    print(f"Packaged Career Agent OS extension {manifest['version']} for {api_base}")
    print(f"Web app: {web_base}")
    print(f"Unpacked: {output_dir}")
    print(f"Zip: {zip_path}")
    return 0


def normalize_api_base(value: str) -> str:
    parsed = urlparse(value.strip().rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit("--api must be an absolute http(s) URL, for example https://api.example.com")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def normalize_web_base(value: str) -> str:
    parsed = urlparse(value.strip().rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit("--web must be an absolute http(s) URL, for example https://app.example.com")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def safe_release_name(api_base: str, version: str) -> str:
    parsed = urlparse(api_base)
    host = parsed.netloc.replace(":", "-")
    suffix = f"-v{version}" if version else ""
    return f"{host}{suffix}"


def copy_extension_files(output_dir: Path) -> None:
    for source in EXTENSION_DIR.iterdir():
        if source.is_file():
            shutil.copy2(source, output_dir / source.name)


def update_manifest(manifest_path: Path, api_base: str, version: str) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if version:
        manifest["version"] = version
    manifest["host_permissions"] = [f"{api_origin(api_base)}/*"]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def write_config(config_path: Path, api_base: str, web_base: str) -> None:
    config_path.write_text(
        "window.CAREER_AGENT_OS_EXTENSION_CONFIG = {\n"
        f"  apiBaseUrl: {json.dumps(api_base)},\n"
        f"  webAppUrl: {json.dumps(web_base)},\n"
        "};\n",
        encoding="utf-8",
    )


def write_release_metadata(metadata_path: Path, version: str, api_base: str, web_base: str, output_dir: Path, zip_path: Path) -> None:
    metadata_path.write_text(
        json.dumps(
            {
                "name": "Career Agent OS Extension",
                "version": version,
                "apiBaseUrl": api_base,
                "webAppUrl": web_base,
                "packagedFor": api_origin(api_base),
                "packagedAt": datetime.now(UTC).isoformat(),
                "unpackedPath": str(output_dir.resolve()),
                "zipPath": str(zip_path.resolve()),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def api_origin(api_base: str) -> str:
    parsed = urlparse(api_base)
    return f"{parsed.scheme}://{parsed.netloc}"


def create_zip(source_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.iterdir()):
            if path.is_file():
                archive.write(path, arcname=path.name)


if __name__ == "__main__":
    sys.exit(main())
