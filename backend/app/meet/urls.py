"""Google Meet URL checks.

Accepted links are HTTPS URLs on meet.google.com:
- a meeting code such as https://meet.google.com/abc-defg-hij
- a lookup link such as https://meet.google.com/lookup/abcdefghij

Optional query parameters are kept when they are short and do not redirect.
The app cannot tell whether a saved link has expired. That needs the Google
Meet API, which is not configured.
"""

import re
from urllib.parse import parse_qsl, urlencode, urlsplit

_CODE = re.compile(r"^[a-z]{3}-[a-z]{4}-[a-z]{3}$")
_LOOKUP = re.compile(r"^[A-Za-z0-9_-]{10,64}$")
_QUERY_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,20}$")
_QUERY_VALUE = re.compile(r"^[A-Za-z0-9._~-]{0,64}$")
_BLOCKED_QUERY = frozenset({"continue", "redirect", "url", "next", "q", "dest"})


class MeetUrlError(ValueError):
    """The value is not a Google Meet HTTPS URL this app can store or open."""


def meet_link_status(url: str | None) -> str:
    return "added" if url else "missing"


def normalize_meet_url(value: str) -> str:
    raw = value.strip()
    if not raw or len(raw) > 300:
        raise MeetUrlError("Enter a valid Google Meet link.")
    if any(character.isspace() or ord(character) < 32 or character == "\\" for character in raw):
        raise MeetUrlError("Enter a valid Google Meet link.")
    try:
        parts = urlsplit(raw)
    except ValueError as exc:
        raise MeetUrlError("Enter a valid Google Meet link.") from exc
    if parts.scheme != "https" or parts.hostname != "meet.google.com":
        raise MeetUrlError("Enter a valid Google Meet link.")
    if parts.username or parts.password or parts.fragment or parts.port not in {None, 443}:
        raise MeetUrlError("Enter a valid Google Meet link.")
    trimmed_path = parts.path.rstrip("/") or "/"
    segments = [segment for segment in trimmed_path.split("/") if segment]
    if trimmed_path != "/" + "/".join(segments):
        raise MeetUrlError("Enter a valid Google Meet link.")
    if len(segments) == 1 and _CODE.fullmatch(segments[0].lower()):
        path = segments[0].lower()
    elif len(segments) == 2 and segments[0].lower() == "lookup" and _LOOKUP.fullmatch(segments[1]):
        path = f"lookup/{segments[1]}"
    else:
        raise MeetUrlError("Enter a valid Google Meet link.")
    try:
        pairs = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise MeetUrlError("Enter a valid Google Meet link.") from exc
    if len(pairs) > 6:
        raise MeetUrlError("Enter a valid Google Meet link.")
    for key, item in pairs:
        if key.lower() in _BLOCKED_QUERY or not _QUERY_KEY.fullmatch(key) or not _QUERY_VALUE.fullmatch(item):
            raise MeetUrlError("Enter a valid Google Meet link.")
    canonical = f"https://meet.google.com/{path}"
    if pairs:
        canonical = f"{canonical}?{urlencode(pairs)}"
    if len(canonical) > 300:
        raise MeetUrlError("Enter a valid Google Meet link.")
    return canonical
