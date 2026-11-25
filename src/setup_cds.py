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


def save_token(token, path, replace=False):
    """Preserve existing credentials by default; replace atomically on request."""
    if not token or token != token.strip() or any(c.isspace() for c in token):
        raise ValueError("Paste one non-empty Personal Access Token, without spaces or line breaks.")
    if token.startswith("<") or len(token) > 4096:
        raise ValueError("Paste the actual token from your CDS profile.")
    path = Path(path)
    if replace:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError("The CDS configuration is a link or special file; it was preserved.")
        descriptor, name = tempfile.mkstemp(prefix=".cdsapirc-", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w") as output:
                os.fchmod(output.fileno(), 0o600)
                output.write(f"url: {API}\nkey: {json.dumps(token)}\n")
                output.flush()
                os.fsync(output.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(f"url: {API}\nkey: {json.dumps(token)}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true", help="Privately enter a replacement key, preserving the old file until the new input is valid.")
    args = parser.parse_args()
    path = Path.home() / ".cdsapirc"
    if (path.exists() or path.is_symlink()) and not args.replace:
        print("A CDS configuration already exists. It was preserved; no token was read or displayed.")
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
