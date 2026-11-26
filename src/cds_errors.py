"""Turn CDS failures into useful instructions without echoing provider secrets.

Most failures select a fixed message. HTTP 400/422 can also include a bounded,
redacted provider reason; raw exceptions and unfiltered bodies are never
returned because they can contain credentials or signed download URLs.
"""
from __future__ import annotations

import json
import re


def provider_detail(response, secret_values=()):
    """Return a short redacted reason, never credentials or download URLs."""
    try:
        payload = response.json()
    except (AttributeError, ValueError, TypeError):
        payload = getattr(response, "text", "")
    if isinstance(payload, dict):
        payload = next((payload[key] for key in ("detail", "message", "error", "reason", "title") if payload.get(key)), "")

    def clean(value):
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()
                    if not re.search(r"token|secret|password|authorization|credential|cookie|session|signature|access.?key|url|uri|location|^key$|api.?key", key, re.I)}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    payload = clean(payload)
    text = payload if isinstance(payload, str) else json.dumps(payload)
    for secret in sorted((x for x in secret_values if isinstance(x, str) and x), key=len, reverse=True):
        text = text.replace(secret, "[private value removed]")
    text = re.sub(r"https?://[^\s<>\"']+", "[URL removed]", text, flags=re.I)
    text = re.sub(r"\bBearer\s+\S+", "[authorization removed]", text, flags=re.I)
    text = re.sub(r"\b(?:api[_ -]?key|token|password|secret|authorization)\s*[:=]\s*[^\s,;]+", "[private field removed]", text, flags=re.I)
    text = re.sub(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", "[identifier removed]", text, flags=re.I)
    text = re.sub(r"[A-Za-z0-9_+/=-]{24,}", "[long value removed]", text)
    return " ".join(text.split())[:800]


def retrieval_error(error, secret_values=()):
    status = None
    descriptions, kinds, details = [], [], []
    seen = set()
    current = error
    while current is not None and id(current) not in seen and len(seen) < 8:
        seen.add(id(current))
        kinds.append(type(current).__name__)
        descriptions.append(str(current).lower())
        response = getattr(current, "response", None)
        if response is not None:
            code = getattr(response, "status_code", None)
            if isinstance(code, int) and 100 <= code <= 599:
                status = code
                if code in (400, 422):
                    details.append(provider_detail(response, secret_values))
            try:
                descriptions.append(json.dumps(response.json()).lower())
            except (AttributeError, ValueError, TypeError):
                pass
        current = current.__cause__ or current.__context__
    description = " ".join(descriptions)
    licence_required = ("licen" in description or "terms" in description) and any(
        phrase in description for phrase in (
            "not accepted", "not_accepted", "must accept", "please accept", "need to accept",
            "unaccepted", "missing required licences", "missing required licenses", "missing licence",
            "missing license", "accept the licence", "accept the license", "accept these terms"))
    label = f"CDS request failed (HTTP {status})." if status else "CDS request did not finish."
    if status == 401:
        hint = ("The service rejected the credentials. First check older quoted configurations with: "
                "python src/setup_cds.py --repair. If the error persists, copy the current API key from your CDS profile "
                "and run: python src/setup_cds.py --replace")
    elif status == 403 and licence_required:
        hint = ("The provider reports a licence/terms requirement. Sign into the same CDS account, "
                "open CERRA-Land's Download page, scroll to Terms of use and accept the licence, then retry --probe.")
    elif status == 403:
        hint = ("Access was forbidden. Check the CERRA-Land licence and your CDS account/profile. "
                "If the API key changed, run: python src/setup_cds.py --replace")
    elif status in (400, 422):
        fields = ("variable", "level_type", "product_type", "year", "month", "day", "time",
                  "leadtime_hour", "data_format", "download_format", "data_type", "area", "soil_layer")
        named = [field for field in fields if re.search(r"\b" + field + r"\b", description)]
        hint = "The provider rejected the request or retrieval. Keep the original request plan for diagnosis."
        if named:
            hint += " Selection fields mentioned: " + ", ".join(named) + "."
        detail = next((item for item in details if item and item not in ("{}", "[]")), "")
        if detail:
            hint += " Provider reason (redacted): " + detail
    elif status == 404:
        hint = "The requested service or resource was not found. Check CDS status and the current dataset API endpoint."
    elif status == 429:
        hint = "The service rate or queue limit was reached. Keep the caches and retry later."
    elif status is not None and status >= 500:
        hint = "The provider returned a service error. Check CDS live status and retry later; cached results are retained."
    elif any("Timeout" in kind or "ConnectionError" in kind for kind in kinds):
        hint = "A connection or timeout interrupted the request. Check the connection and CDS live status, then retry."
    elif any(kind in ("ScannerError", "ParserError") for kind in kinds) or (
            "configuration" in description and ("missing" in description or "incomplete" in description)):
        hint = "The private CDS configuration could not be loaded. Re-enter the current API key with: python src/setup_cds.py --replace"
    else:
        hint = ("The client failed before a usable download was returned. Check the account, licence and CDS live status. "
                "If this persists, report this message without sharing your key.")
    return label + " " + hint + " No published snow tables were replaced."
