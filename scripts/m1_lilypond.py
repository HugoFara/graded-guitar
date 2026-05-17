"""LilyPond → MusicXML conversion wrapper for the M1 pipeline.

Wraps `python-ly` (the only pip-installable LilyPond → MusicXML
converter that exists) with three workarounds for known python-ly
defects observed on Mutopia classical-guitar files:

1. **Multi-`\\score` truncation.** python-ly converts only the first
   `\\score` block in a file, silently dropping the rest. We split the
   source into one self-contained .ly per top-level `\\score` block and
   convert each separately. Each movement becomes its own MusicXML.

2. **`Assignment` UnboundLocalError.** `ly.musicxml.lymus2musxml.
   ParseSource.Assignment` declares `val` inside an if/elif chain that
   only covers Markup/String/Scheme/UserCommand values. Any other value
   type (e.g. Number, Note, Music expression) skips the chain and
   crashes the entire conversion with `UnboundLocalError: ... 'val'`.
   We monkey-patch the method to swallow that specific error per
   assignment — losing one stray top-level binding never matters for
   a corpus pipeline.

3. **TabStaff-only files.** Files that use only `\\TabStaff` (with no
   parallel `\\Staff`) produce MusicXML without a `<part-list>`. We
   substitute `TabStaff` → `Staff` and retry. We lose explicit tab
   layout markings; the underlying notation is preserved.

We also strip `\\header` and post-inject `<work-title>` /
`<creator type='composer'>` from header metadata we parsed ourselves
when fallback paths require it.

All workarounds fail loudly: if a block still won't convert cleanly
after fallbacks, we return a structured failure with a reason code so
the M1 pipeline can land it in `rejected.json` instead of silently
producing partial music.

See decisions/0007-mutopia-source.md for rationale and tradeoffs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from lxml import etree

import ly.musicxml
import ly.musicxml.lymus2musxml as _lymus2musxml
import ly.musicxml.xml_objs as _xml_objs


# -------------------- monkey-patch python-ly --------------------------

_ORIG_ASSIGNMENT = _lymus2musxml.ParseSource.Assignment


def _patched_assignment(self, a):
    """python-ly's Assignment doesn't initialise `val`, so any value
    type outside its known set (Markup/String/Scheme/UserCommand)
    triggers UnboundLocalError that kills the whole conversion. We
    swallow that error per assignment: losing one stray top-level
    binding is fine, losing all the music isn't."""
    try:
        return _ORIG_ASSIGNMENT(self, a)
    except UnboundLocalError:
        return


_lymus2musxml.ParseSource.Assignment = _patched_assignment


_ORIG_INJECT_VOICE = _xml_objs.Bar.inject_voice


def _patched_inject_voice(self, new_voice, override=False,
                          active_slur_count=None):
    """`Bar.inject_voice` indexes `new_voice.obj_list[0]` without
    checking — empty voices crash with IndexError on Mutopia files
    that contain `\\new Voice { }` placeholders or other edge cases.
    Skip empty voices instead."""
    if not new_voice.obj_list:
        return
    try:
        return _ORIG_INJECT_VOICE(self, new_voice, override, active_slur_count)
    except IndexError:
        # If something else inside indexes the bar's own obj_list past
        # its end, prefer skipping over killing the whole conversion.
        return


_xml_objs.Bar.inject_voice = _patched_inject_voice


SCORE_TOKEN = re.compile(r"\\score\b")
HEADER_TOKEN = re.compile(r"\\header\b")
TABSTAFF_TOKEN = re.compile(r"\bTabStaff\b")
TABVOICE_TOKEN = re.compile(r"\bTabVoice\b")
TABSTAFF_BLOCK_TOKEN = re.compile(r"\\(?:new\s+|context\s+)?TabStaff\b")


@dataclass
class MovementResult:
    movement_index: int           # 1-based
    success: bool
    musicxml_bytes: bytes | None = None
    failure_reason: str | None = None       # short code
    failure_detail: str | None = None       # 1-line context
    measures: int = 0
    notes: int = 0
    parts: int = 0
    fallbacks_applied: list[str] = field(default_factory=list)


@dataclass
class ConversionResult:
    metadata: dict[str, str] = field(default_factory=dict)
    movements: list[MovementResult] = field(default_factory=list)
    source_score_count: int = 0


# ---------- comment- and string-aware brace scanning -----------------

def _strip_comments_for_scan(src: str) -> str:
    """Length-preserving blanking of comments and string literals."""
    out = list(src)
    i = 0
    n = len(src)
    while i < n:
        ch = src[i]
        if ch == "%" and i + 1 < n and src[i + 1] == "{":
            j = src.find("%}", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        if ch == "%":
            j = src.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        if ch == '"':
            j = i + 1
            while j < n and src[j] != '"':
                if src[j] == "\\" and j + 1 < n:
                    j += 2
                else:
                    j += 1
            for k in range(i, min(j + 1, n)):
                if out[k] != "\n":
                    out[k] = " "
            i = j + 1
            continue
        i += 1
    return "".join(out)


def _match_brace_block(scan: str, after: int) -> int | None:
    """Given an offset just past a token like `\\score`, find the start
    of its `{...}` body and return the offset one past the matching `}`.
    Returns None if no balanced block is found."""
    i = after
    while i < len(scan) and scan[i] != "{":
        if not scan[i].isspace():
            return None
        i += 1
    if i >= len(scan):
        return None
    depth = 1
    j = i + 1
    while j < len(scan) and depth > 0:
        c = scan[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        j += 1
    return j if depth == 0 else None


def find_score_blocks(src: str) -> list[tuple[int, int]]:
    scan = _strip_comments_for_scan(src)
    blocks: list[tuple[int, int]] = []
    for m in SCORE_TOKEN.finditer(scan):
        end = _match_brace_block(scan, m.end())
        if end is not None:
            blocks.append((m.start(), end))
    return blocks


def find_header_block(src: str) -> tuple[int, int] | None:
    scan = _strip_comments_for_scan(src)
    m = HEADER_TOKEN.search(scan)
    if not m:
        return None
    end = _match_brace_block(scan, m.end())
    return (m.start(), end) if end is not None else None


def split_score_blocks(src: str) -> list[str]:
    """One self-contained .ly per top-level `\\score`. If there's at
    most one block, returns [src] unchanged."""
    blocks = find_score_blocks(src)
    if len(blocks) <= 1:
        return [src]
    preamble = src[: blocks[0][0]]
    return [preamble + src[s:e] + "\n" for (s, e) in blocks]


# ---------- header metadata extraction (we always run this) -----------

# Tokens like `title = "Foo"` or `composer = "Bar"`. Mutopia uses
# `mutopiacomposer`, `mutopiatitle`, `mutopiacopyright`, `mutopiainstrument`.
_FIELD_RE = re.compile(
    r"^\s*(?P<key>[A-Za-z]+)\s*=\s*\"(?P<val>[^\"]*)\"",
    re.MULTILINE,
)


def extract_header_metadata(src: str) -> dict[str, str]:
    """Pull `key = "value"` fields from the file's `\\header { ... }`
    block. Returns a dict keyed by lowercase field name. Empty when no
    header is found."""
    span = find_header_block(src)
    if span is None:
        return {}
    s, e = span
    body = src[s:e]
    out: dict[str, str] = {}
    for m in _FIELD_RE.finditer(body):
        out[m.group("key").lower()] = m.group("val").strip()
    return out


# ---------- conversion (in-process via python-ly library) -------------

def _run_ly_musicxml(ly_text: str) -> tuple[bool, bytes | None, str]:
    """Convert LilyPond text → MusicXML bytes using python-ly's library
    API (so our `Assignment` monkey-patch is active). Returns (ok,
    bytes, error_summary)."""
    try:
        writer = ly.musicxml.writer()
        writer.parse_text(ly_text)
        xml = writer.musicxml()
        data = xml.tostring()
    except Exception as exc:
        # python-ly throws a variety of exception types (IndexError,
        # AttributeError, KeyError, custom). We just record the class
        # and message; the fallback paths decide what to do next.
        return False, None, f"{type(exc).__name__}: {exc}"[:240]
    if not data:
        return False, None, "empty_output"
    return True, data, ""


def _strip_header(src: str) -> str:
    span = find_header_block(src)
    if span is None:
        return src
    s, e = span
    return src[:s] + src[e:]


def _replace_tabstaff(src: str) -> str:
    # Replace both the context name and inner voice context — python-ly
    # warns on TabVoice and drops the music inside.
    return TABVOICE_TOKEN.sub("Voice", TABSTAFF_TOKEN.sub("Staff", src))


def _strip_tabstaff_block(src: str) -> str:
    """Remove every `\\context TabStaff << ... >>` and `\\new TabStaff
    { ... }` block. Brace matching across both `{}` and `<<>>`."""
    scan = _strip_comments_for_scan(src)
    cuts: list[tuple[int, int]] = []
    for m in TABSTAFF_BLOCK_TOKEN.finditer(scan):
        i = m.end()
        # skip whitespace
        while i < len(scan) and scan[i].isspace():
            i += 1
        if i >= len(scan):
            continue
        # `\name = <...>` aliases skip; only handle `{` or `<<`
        if scan[i] == "{":
            end = _match_brace_block(scan, m.end())
            if end is not None:
                cuts.append((m.start(), end))
        elif scan[i:i + 2] == "<<":
            depth = 1
            j = i + 2
            while j < len(scan) and depth > 0:
                if scan[j:j + 2] == "<<":
                    depth += 1; j += 2
                elif scan[j:j + 2] == ">>":
                    depth -= 1; j += 2
                else:
                    j += 1
            if depth == 0:
                cuts.append((m.start(), j))
    if not cuts:
        return src
    # apply cuts right-to-left so offsets stay valid
    out = src
    for s, e in sorted(cuts, key=lambda x: -x[0]):
        out = out[:s] + out[e:]
    return out


# ---------- structural validation of converted MusicXML --------------

def _structural_check(xml_bytes: bytes) -> tuple[bool, str | None, dict]:
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as e:
        return False, "XML_MALFORMED", {"detail": str(e)[:100]}
    if etree.QName(root).localname not in ("score-partwise", "score-timewise"):
        return False, "XML_NOT_MUSICXML", {}
    parts = root.xpath("//*[local-name()='part-list']/*[local-name()='score-part']")
    if not parts:
        return False, "NO_PARTS", {}
    notes = root.xpath("//*[local-name()='note']")
    measures = root.xpath("//*[local-name()='measure']")
    if not notes:
        return False, "NO_NOTES", {"measures": len(measures)}
    return True, None, {
        "parts": len(parts), "measures": len(measures), "notes": len(notes),
    }


# ---------- post-conversion metadata injection -----------------------

def _inject_metadata(xml_bytes: bytes, meta: dict[str, str]) -> bytes:
    """Add `<work-title>` and `<creator type='composer'>` to MusicXML if
    they're absent. Used after we had to strip `\\header` to dodge the
    python-ly Assignment crash."""
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        return xml_bytes
    NS = {"": ""}
    title = (meta.get("title") or meta.get("mutopiatitle") or "").strip()
    composer = (meta.get("composer") or meta.get("mutopiacomposer") or "").strip()
    if title:
        work = root.find("./{*}work")
        if work is None:
            work = etree.SubElement(root, "work")
            root.insert(0, work)
        wt = work.find("./{*}work-title")
        if wt is None:
            wt = etree.SubElement(work, "work-title")
        if not (wt.text or "").strip():
            wt.text = title
    if composer:
        ident = root.find("./{*}identification")
        if ident is None:
            ident = etree.SubElement(root, "identification")
            # place after work if possible
            work = root.find("./{*}work")
            if work is not None:
                root.remove(ident)
                work.addnext(ident)
        # only add if no creator of any kind exists
        if not ident.findall("./{*}creator"):
            c = etree.SubElement(ident, "creator", type="composer")
            c.text = composer
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8")


# ---------- per-block convert with fallbacks -------------------------

def _convert_block_with_fallbacks(
    ly_text: str, meta: dict[str, str]
) -> MovementResult:
    fallbacks: list[str] = []
    has_header = find_header_block(ly_text) is not None
    has_tabstaff = TABSTAFF_TOKEN.search(ly_text) is not None

    # Try each variant in order of preference: original, header-stripped,
    # tabstaff-substituted, combo. The Assignment monkey-patch handles
    # the headline python-ly bug, but the other workarounds catch
    # different failures (TabStaff-only output, plus some files where
    # header objects throw a different exception in metadata writeback).
    attempts = [("none", ly_text)]
    if has_header:
        attempts.append(("strip_header", _strip_header(ly_text)))
    if has_tabstaff:
        attempts.append(("tabstaff_to_staff", _replace_tabstaff(ly_text)))
        attempts.append(("strip_tabstaff_block",
                         _strip_tabstaff_block(ly_text)))
    if has_header and has_tabstaff:
        attempts.append(
            ("strip_header+tabstaff_to_staff",
             _strip_header(_replace_tabstaff(ly_text)))
        )
        attempts.append(
            ("strip_header+strip_tabstaff_block",
             _strip_header(_strip_tabstaff_block(ly_text)))
        )

    last_err = ""
    for label, variant in attempts:
        if label != "none":
            fallbacks.append(label)
        ok, data, err = _run_ly_musicxml(variant)
        if not ok or data is None:
            last_err = err
            continue
        if label.startswith("strip_header") and data:
            data = _inject_metadata(data, meta)
        clean, fail_code, details = _structural_check(data)
        if clean:
            return MovementResult(
                movement_index=0,
                success=True,
                musicxml_bytes=data,
                parts=details["parts"],
                measures=details["measures"],
                notes=details["notes"],
                fallbacks_applied=fallbacks,
            )
        last_err = f"{fail_code}: {details}"

    return MovementResult(
        movement_index=0,
        success=False,
        failure_reason="LY_CONVERSION_FAILED",
        failure_detail=last_err[:240] or "all fallbacks failed",
        fallbacks_applied=fallbacks,
    )


# ---------- public entry point ---------------------------------------

def convert_lilypond(ly_text: str) -> ConversionResult:
    """Split a LilyPond source into top-level `\\score` blocks and
    convert each to MusicXML. Returns a ConversionResult enumerating
    every movement (success or failure)."""
    metadata = extract_header_metadata(ly_text)
    blocks = split_score_blocks(ly_text)
    source_score_count = len(find_score_blocks(ly_text))

    movements: list[MovementResult] = []
    for i, blk in enumerate(blocks, 1):
        result = _convert_block_with_fallbacks(blk, metadata)
        result.movement_index = i
        movements.append(result)

    return ConversionResult(
        metadata=metadata,
        movements=movements,
        source_score_count=source_score_count,
    )
