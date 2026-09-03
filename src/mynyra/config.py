"""Credential input with deliberately uninformative representations/errors."""

import json
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path


class ProbeError(Exception):
    """A diagnostic safe to display without remote payloads or secrets."""


@dataclass(frozen=True)
class Credentials:
    client_id: str = field(repr=False)
    client_secret: str = field(repr=False)
    access_token: str = field(default="", repr=False)


def load_credentials(path: Path | None, *, account: bool) -> Credentials:
    names = ("client_id", "client_secret", "access_token")
    if path is None:
        values = {name: os.environ.get(f"CTRADER_{name.upper()}", "") for name in names}
    else:
        try:
            if stat.S_IMODE(path.stat().st_mode) & 0o077:
                raise ProbeError("Credential file must be readable only by its owner (chmod 600).")
            values = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ProbeError("Cannot read a valid credential JSON file.") from None
        if not isinstance(values, dict):
            raise ProbeError("Credential JSON must be an object.")
    required = names if account else names[:2]
    for name in required:
        value = values.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ProbeError(f"Missing {name}; supply the credential file or CTRADER_{name.upper()}.")
    return Credentials(
        client_id=values["client_id"].strip(),
        client_secret=values["client_secret"].strip(),
        access_token=values["access_token"].strip() if account else "",
    )
