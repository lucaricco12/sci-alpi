"""Configure the private CDS token interactively, outside the repository."""
from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import warnings

API = "https://cds.climate.copernicus.eu/api"


def save_token(token, path):
    """Exclusive creation prevents accidentally replacing existing credentials."""
    if not token or token != token.strip() or any(c.isspace() for c in token):
        raise ValueError("Paste one non-empty Personal Access Token, without spaces or line breaks.")
    if token.startswith("<") or len(token) > 4096:
        raise ValueError("Paste the actual token from your CDS profile.")
    path = Path(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(f"url: {API}\nkey: {json.dumps(token)}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    path = Path.home() / ".cdsapirc"
    if path.exists() or path.is_symlink():
        print("A CDS configuration already exists. It was preserved; no token was read or displayed.")
        return
    print("First create your ECMWF/CDS account and accept the CERRA-Land licence in your browser.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            token = getpass.getpass("Paste your CDS Personal Access Token here (hidden): ")
        save_token(token, path)
    except (getpass.GetPassWarning, EOFError):
        parser.exit(2, "Use the Codespace's integrated terminal, which supports hidden input. No token was saved.\n")
    except (ValueError, FileExistsError) as error:
        parser.exit(2, str(error) + "\n")
    print("Private CDS configuration saved with owner-only permissions, outside the repository.")
    print("Next: python src/cerra_land.py --probe")


if __name__ == "__main__":
    main()
