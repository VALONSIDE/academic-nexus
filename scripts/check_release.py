"""Read-only release checks. Never stage, commit, tag, publish, or print secrets."""

import argparse
import ast
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True)
    return result.stdout.decode("utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-local-secrets", action="store_true",
                        help="Compare private .env credentials to public files without displaying values")
    args = parser.parse_args()
    failures = []
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"alpha-\d{4}-NR", version):
        failures.append("VERSION: unexpected product label")
    package_version = "0.1.0-alpha." + version.removeprefix("alpha-").replace("-", "")
    for filename in ("frontend/package.json", "frontend/package-lock.json"):
        data = json.loads((ROOT / filename).read_text(encoding="utf-8"))
        if data["version"] != package_version or ("packages" in data and data["packages"][""]["version"] != package_version):
            failures.append(f"{filename}: inconsistent package version")
    for filename in ("backend/app/core/config.py", "frontend/src/version.ts", ".env.example", "scripts/manage.sh"):
        content = (ROOT / filename).read_text(encoding="utf-8")
        if version not in content or "alpha-0823-NR" in content:
            failures.append(f"{filename}: inconsistent product version")
    source = (ROOT / "backend/app/core/config.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    configured = [node.value.value for node in ast.walk(tree)
                  if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                  and node.target.id == "app_version" and isinstance(node.value, ast.Constant)]
    if configured != [version]:
        failures.append("API default version differs from VERSION")
    for filename in git("ls-files", "-ci", "--exclude-standard").splitlines():
        failures.append(f"Ignored file is tracked: {filename}")
    public_files = sorted(set(git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split("\0")) - {""})
    secrets = []
    if args.check_local_secrets and (ROOT / ".env").exists():
        secret_names = {"MINIMAX_API_KEY", "SILICONFLOW_API_KEY", "JWT_SECRET_KEY", "ACCESS_KEY_PEPPER",
                        "POSTGRES_PASSWORD", "INITIAL_ADMIN_PASSWORD"}
        for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
            name, separator, value = line.partition("=")
            value = value.strip().strip("\"'")
            if separator and name.strip() in secret_names and len(value) >= 12 and not value.startswith("CHANGE_ME"):
                secrets.append(value)
    suspect = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{24,}")
    for filename in public_files:
        path = ROOT / filename
        if not path.is_file() or path.is_symlink():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        if suspect.search(content) or any(value in content for value in secrets):
            failures.append(f"Possible credential in public file: {filename} (value hidden)")
    if git("log", "--all", "--format=", "--name-only", "--", ".env").strip():
        failures.append("Private .env appears in Git history; inspect before publishing")
    whitespace = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True)
    if whitespace.returncode:
        failures.append("git diff --check reported whitespace errors")
    print(json.dumps({"version": version, "public_files_checked": len(public_files),
                      "local_secret_comparison": args.check_local_secrets, "failures": failures}, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
