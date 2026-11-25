"""Configure the private CDS token interactively, outside the repository."""
from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import tempfile
import warnings

API = "https://cds.climate.copernicus.eu/api"


def validate_token(token):
    if not isinstance(token, str) or not token or token != token.strip() or any(c.isspace() for c in token) or not token.isprintable():
        raise ValueError("Paste one non-empty Personal Access Token, without spaces or line breaks.")
    if token.startswith("<") or len(token) > 4096:
        raise ValueError("Paste the actual token from your CDS profile.")
    if token[0] in "\"'" or token[-1] in "\"'":
        raise ValueError("Copy the API key itself without surrounding quotes. Use --repair for an older saved configuration.")


def write_private(contents, path, replace=False):
    """Preserve existing files by default; replace atomically on request."""
    path = Path(path)
    if replace:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError("The CDS configuration is a link or special file; it was preserved.")
        descriptor, name = tempfile.mkstemp(prefix=".cdsapirc-", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w") as output:
                os.fchmod(output.fileno(), 0o600)
                output.write(contents)
                output.flush()
                os.fsync(output.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(contents)


def save_token(token, path, replace=False):
    """CDS uses a simple key:value reader, which keeps literal quote marks."""
    validate_token(token)
    write_private(f"url: {API}\nkey: {token}\n", path, replace=replace)


def repair_configuration(path):
    """Remove JSON quotes from an older setup file without displaying its key.

    Preserve the other lines and refuse ambiguous/malformed input. This fixes
    storage format only; it does not check whether the account accepts the key.
    """
    path = Path(path)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("The CDS configuration is a link or special file; it was preserved.")
    if not path.is_file():
        raise ValueError("No saved CDS configuration found. Run python src/setup_cds.py first.")
    before = path.read_bytes()
    try:
        text = before.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("The configuration encoding is invalid. Use --replace to enter the current key privately.") from None
    lines = text.splitlines(keepends=True)
    entries = [(index, line.split(":", 1)[1].strip()) for index, line in enumerate(lines)
               if ":" in line and line.split(":", 1)[0].strip() == "key"]
    if len(entries) != 1:
        raise ValueError("The configuration must have exactly one key entry. It was preserved; use --replace.")
    index, value = entries[0]
    if not (value.startswith('"') and value.endswith('"')):
        validate_token(value)
        return False
    try:
        token = json.loads(value)
    except json.JSONDecodeError:
        raise ValueError("The stored key has an invalid quoted format. It was preserved; use --replace.") from None
    validate_token(token)
    ending = "\r\n" if lines[index].endswith("\r\n") else "\n" if lines[index].endswith("\n") else ""
    lines[index] = f"key: {token}{ending}"
    if path.read_bytes() != before:
        raise RuntimeError("The configuration changed during repair. Retry without changing it elsewhere.")
    write_private("".join(lines), path, replace=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--replace", action="store_true", help="Privately enter a replacement key, preserving the old file until the new input is valid.")
    mode.add_argument("--repair", action="store_true", help="Fix extra quotes written by the older setup without re-entering or displaying the key.")
    args = parser.parse_args()
    path = Path.home() / ".cdsapirc"
    if args.repair:
        try:
            changed = repair_configuration(path)
        except (OSError, ValueError, RuntimeError) as error:
            parser.exit(2, str(error) + "\n")
        print("Private CDS key format repaired. You do not need to paste your key again." if changed
              else "The saved CDS key is already unquoted. No change was needed.")
        if os.environ.get("CDSAPI_KEY") or os.environ.get("CDSAPI_RC"):
            print("An environment setting may override this file. To use the repaired file in this shell, run: unset CDSAPI_KEY CDSAPI_RC")
        print("Next: python src/cerra_land.py --probe")
        return
    if (path.exists() or path.is_symlink()) and not args.replace:
        print("A CDS configuration already exists. It was preserved; no token was read or displayed.")
        print("For extra quotes from an older setup: python src/setup_cds.py --repair")
        print("To update it after changing your API key: python src/setup_cds.py --replace")
        return
    print("First create your ECMWF/CDS account and accept the CERRA-Land licence in your browser.")
    print("Enter the API key only at the hidden prompt below. Input will stay invisible.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            token = getpass.getpass("Paste your CDS Personal Access Token here (hidden): ").strip()
        save_token(token, path, replace=args.replace)
    except (getpass.GetPassWarning, EOFError):
        parser.exit(2, "Use the Codespace's integrated terminal, which supports hidden input. No token was saved.\n")
    except (ValueError, FileExistsError) as error:
        parser.exit(2, str(error) + "\n")
    print("Private CDS configuration saved with owner-only permissions, outside the repository.")
    print("Setup finished. You are returning to the shell, where a line ending in $ expects a command.")
    print("Run this command next: python src/cerra_land.py --probe")


if __name__ == "__main__":
    main()
