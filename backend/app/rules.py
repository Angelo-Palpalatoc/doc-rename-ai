from __future__ import annotations

import re
from collections.abc import Collection

CERTIFY_ANCHOR = re.compile(r"this\s+is\s+to\s+certify\s+that\s*[:.,-]*\s*", re.IGNORECASE)
ARTICLES_ANCHOR = re.compile(
    r"articles\s+of\s+(?:incorporation|partnership)(?:\s+(?:and|&)\s+by[\s-]*laws)?\s+of\s*[:.,-]*\s*",
    re.IGNORECASE,
)
ARTICLES_HEADING = re.compile(
    r"^\s*articles\s+of\s+(?:incorporation|partnership)\s*(?:of\s*:?)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
FIRST_CLAUSE = re.compile(
    r"\bfirst\s*[:.\-]?\s*(?:that\s+)?(?:the\s+)?name\s+of\s+(?:(?:the|said)\s+)?"
    r"(?:corporation|company|partnership)\s+(?:shall\s+be|is)\s*[:.\-]?\s*",
    re.IGNORECASE,
)
GIS_HEADING = re.compile(r"general\s+information\s+sheet", re.IGNORECASE)
CORPORATE_NAME_FIELD = re.compile(
    r"^\s*(?:\d+[.)]\s*)?corporate\s+name\s*:?\s*",
    re.IGNORECASE | re.MULTILINE,
)
PRESENTATION_ANCHOR = re.compile(
    r"know\s+all\s+(?:persons|men)\s+by\s+these\s+presents\s*:?\s*",
    re.IGNORECASE,
)
CERTIFICATE_HEADING = re.compile(
    r"certificate\s+of\s+(?:incorporation|registration|partnership)\b",
    re.IGNORECASE,
)
SECRETARY_HEADING = re.compile(r"secretary[’']?s?\s+certificate\b", re.IGNORECASE)
SECRETARY_ROLE = re.compile(
    r"\b(?:assistant\s+)?(?:corporate\s+)?secretary\s+of\s+",
    re.IGNORECASE,
)
SECRETARY_STATEMENT = re.compile(
    r"\b(?:do\s+hereby\s+certify|resolved|in\s+witness|subscribed)\b",
    re.IGNORECASE,
)
COMPANY_ALIAS = re.compile(
    r"\(\s*(?:the\s+)?[\"'“”‘’]*(?:corporation|company)\b",
    re.IGNORECASE,
)
CLAUSE_END = re.compile(
    r"\b(which|has been|is hereby|was registered|having complied|a corporation|"
    r"a partnership|were duly|this example|this sample)\b",
    re.IGNORECASE,
)
LEGAL_SUFFIX = re.compile(
    r"\b(incorporated|corporation|company|inc\.?|corp\.?|co\.?|limited|ltd\.?|"
    r"partnership|opc|llc|llp)\s*$",
    re.IGNORECASE,
)
PROSE_NOISE = re.compile(
    r"[!?;:]|\b(?:certificate|certifies|certify|submitted|issued|registered)\b",
    re.IGNORECASE,
)
ARTICLES_PHRASE = re.compile(r"articles\s+of", re.IGNORECASE)
WINDOWS_RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$", re.IGNORECASE)
WHITESPACE = re.compile(r"\s+")
INVALID_FILENAME_CHARS = set('<>:"/\\|?*')


def extract_candidates(text: str) -> list[str]:
    """Extract plausible corporate-holder candidates page by page.

    Processing pages separately ensures a heading on one page cannot authorize
    a company name appearing on another page.
    """
    raw_candidates: list[str] = []
    for page in text.split("\f"):
        for match in CERTIFY_ANCHOR.finditer(page):
            candidate = _read_direct_name(page[match.end() :])
            if candidate:
                raw_candidates.append(candidate)

        if SECRETARY_HEADING.search(page):
            raw_candidates.extend(_read_secretary_names(page))

        if GIS_HEADING.search(page):
            for match in CORPORATE_NAME_FIELD.finditer(page):
                candidate = _read_direct_name(page[match.end() :])
                if candidate:
                    raw_candidates.append(candidate)

        if ARTICLES_HEADING.search(page):
            for match in FIRST_CLAUSE.finditer(page):
                candidate = _read_direct_name(page[match.end() :])
                if candidate:
                    raw_candidates.append(candidate)

        if not CERTIFICATE_HEADING.search(page) and not ARTICLES_HEADING.search(page):
            continue

        for match in ARTICLES_ANCHOR.finditer(page):
            candidate = _read_direct_name(page[match.end() :])
            if candidate:
                raw_candidates.append(candidate)

        for match in PRESENTATION_ANCHOR.finditer(page):
            raw_candidates.extend(_read_presentation_names(page[match.end() :]))

    seen: set[str] = set()
    unique: list[str] = []
    for item in raw_candidates:
        key = WHITESPACE.sub(" ", item.lower())
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _read_secretary_names(page: str) -> list[str]:
    statement = SECRETARY_STATEMENT.search(page)
    intro_end = statement.start() if statement else len(page)
    introduction = page[:intro_end][:2500]
    found: list[str] = []
    for role in SECRETARY_ROLE.finditer(introduction):
        tail = introduction[role.end() :]
        alias = COMPANY_ALIAS.search(tail)
        name_block = tail[: alias.start()] if alias else tail
        candidate = _read_direct_name(name_block)
        if candidate:
            found.append(candidate)
    return found


def _read_direct_name(region: str) -> str | None:
    collected: list[str] = []
    for raw in region.splitlines():
        line = raw.strip()
        if not line:
            continue
        terminator = CLAUSE_END.search(line)
        part = (line[: terminator.start()] if terminator else line).strip().rstrip(",;")
        if part:
            collected.append(part)
        name = " ".join(collected)
        if terminator or LEGAL_SUFFIX.search(name) or len(name) > 180 or len(collected) >= 4:
            break
    candidate = WHITESPACE.sub(" ", " ".join(collected)).strip()
    return candidate if _plausible_name(candidate) else None


def _read_presentation_names(region: str) -> list[str]:
    found: list[str] = []
    collected: list[str] = []
    for raw in region.splitlines()[:8]:
        line = raw.strip()
        if not line:
            continue
        terminator = CLAUSE_END.search(line)
        part = (line[: terminator.start()] if terminator else line).strip().rstrip(",;")
        letters = [ch for ch in part if ch.isalpha()]
        display_block = bool(letters) and (
            sum(1 for ch in letters if ch.isupper()) / len(letters) >= 0.8
        )
        if not display_block or len(part) > 180:
            collected.clear()
        else:
            collected.append(part)
            value = " ".join(collected)
            if _plausible_name(value):
                found.append(value)
                collected.clear()
            elif len(collected) >= 4 or len(value) > 180:
                collected.clear()
        if terminator:
            break
    return found


def _plausible_name(value: str) -> bool:
    if not (4 <= len(value) <= 180) or not LEGAL_SUFFIX.search(value):
        return False
    if ARTICLES_PHRASE.search(value):
        return False
    stem = LEGAL_SUFFIX.sub("", value).strip()
    return any(ch.isalnum() for ch in stem) and not PROSE_NOISE.search(value)


def safe_stem(name: str) -> str:
    """Sanitize a document stem for safe cross-platform filenames."""
    cleaned_chars = [" " if (ord(ch) < 32 or ch in INVALID_FILENAME_CHARS) else ch for ch in name]
    value = WHITESPACE.sub(" ", "".join(cleaned_chars)).strip().rstrip(". ")
    if not value:
        raise ValueError("Enter a verified company name.")
    if len(value) > 140:
        raise ValueError("Shorten the output name to 140 characters or fewer.")
    if WINDOWS_RESERVED.match(value):
        value = f"_{value}"
    return value


def allocate_filename(name: str, extension: str, existing: Collection[str]) -> str:
    """Allocate a collision-free filename using deterministic (1), (2) suffixes."""
    stem = safe_stem(name)
    if not extension.startswith(".") or not extension[1:].isalnum():
        raise ValueError("Unsupported file extension.")
    occupied = {item.lower() for item in existing}
    for index in range(100_000):
        proposal = f"{stem}{extension}" if index == 0 else f"{stem} ({index}){extension}"
        if proposal.lower() not in occupied:
            return proposal
    raise RuntimeError("Too many numbered filenames in the export batch.")
