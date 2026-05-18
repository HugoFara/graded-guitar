"""M1.3 — Validate and normalize raw MusicXML files.

For every fetched file in corpus/raw/, validate that it's well-formed
MusicXML for solo classical guitar, extract canonical metadata, and
record the outcome in corpus/manifest.json (accepted) or
corpus/rejected.json (with a reason code). Also writes corpus/report.md.

Reject reason codes are an enum — see decisions/0005-ingest-pipeline.md.

Usage:
    python scripts/m1_validate.py
    python scripts/m1_validate.py --limit 100

See decisions/0005-ingest-pipeline.md for the architecture.
"""
from __future__ import annotations

import argparse
import io
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from lxml import etree

from m1_common import (
    CACHE_DIR,
    MANIFEST_PATH,
    NORMALIZED_DIR,
    RAW_DIR,
    REJECTED_PATH,
    REPORT_PATH,
    ensure_corpus_dirs,
    load_candidates,
    read_json,
    sha256_bytes,
    write_json_atomic,
)


FETCH_LOG_PATH = CACHE_DIR / "fetch_log.json"

GUITAR_TOKENS = ("guitar", "guitarra", "chitarra", "gitarre")
MUSICXML_ROOTS = ("score-partwise", "score-timewise")

# Placeholder strings that several MuseScore/Finale/Sibelius templates
# leave in when the user never set the metadata. We treat these as
# "missing" rather than "valid composer/title" because pedagogically
# they're useless.
PLACEHOLDER_COMPOSERS = {
    "music21",
    "composer",
    "composer / arranger",
    "compositeur / arrangeur",
    "komponist / arrangeur",
    "compositore / arrangiatore",
    "compositor / arreglista",
    "unknown",
    "anonymous composer",
}
PLACEHOLDER_TITLES = {
    "untitled score",
    "untitled",
    "partition sans titre",
    "unbenannte partitur",
    "partitura sin título",
    "partitura senza titolo",
    "no title",
}

# Path substrings that flag a file as dataset / training / OMR noise
# rather than a real piece of repertoire. Case-insensitive substring match
# against the candidate's GitHub path.
PATH_NOISE_TOKENS = (
    "ear-training",
    "ear_training",
    "/omr",
    "omr_data",
    "musicclassification",
    "/dataset",
    "processed_pdf",
    "training-data",
    "test_files",
    "test-fixtures",
    "/samples/",
    "demo/data",
)

REJECT_CODES = {
    "XML_MALFORMED",
    "XML_NOT_MUSICXML",
    "NO_PARTS",
    "MULTIPLE_PARTS",
    "NON_GUITAR_INSTRUMENT",
    "MISSING_TITLE",
    "MISSING_COMPOSER",
    "PLACEHOLDER_METADATA",
    "PATH_NOISE",
    "DUPLICATE",
    "FETCH_FAILED",
    "MXL_EXTRACTION_FAILED",
    "LY_CONVERSION_FAILED",
    "SUPERSEDED",
}


def extract_score_xml(blob: bytes, fmt: str) -> bytes | tuple[None, str]:
    """For .mxl, unzip and return the score XML; for .musicxml, passthrough."""
    if fmt == "musicxml":
        return blob
    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile:
        return None, "bad_zip"

    # MXL container has a META-INF/container.xml that points to the root score.
    score_name: str | None = None
    try:
        container = zf.read("META-INF/container.xml")
        ctree = etree.fromstring(container)
        rootfile = ctree.find(".//{*}rootfile")
        if rootfile is not None:
            score_name = rootfile.get("full-path")
    except KeyError:
        pass
    except etree.XMLSyntaxError:
        pass

    if score_name is None:
        # Fall back: first .xml or .musicxml entry that isn't in META-INF.
        for name in zf.namelist():
            if name.startswith("META-INF/"):
                continue
            if name.lower().endswith((".xml", ".musicxml")):
                score_name = name
                break
    if score_name is None:
        return None, "no_score_xml_in_mxl"
    try:
        return zf.read(score_name)
    except KeyError:
        return None, "score_name_not_found_in_mxl"


def parse_score(xml_bytes: bytes) -> etree._Element | tuple[None, str]:
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:
        return None, f"XML_MALFORMED: {exc}"
    tag = etree.QName(root).localname
    if tag not in MUSICXML_ROOTS:
        return None, f"XML_NOT_MUSICXML: root={tag}"
    return root


def find_text(root: etree._Element, path: str) -> str:
    """Find by tag-only XPath (namespace-agnostic), return stripped text or ''."""
    nodes = root.xpath(path)
    if not nodes:
        return ""
    node = nodes[0]
    text = node.text if hasattr(node, "text") else str(node)
    return (text or "").strip()


def collect_instrument_tokens(root: etree._Element) -> list[str]:
    """Pull every instrument-naming string we can find in the part list."""
    tokens: list[str] = []
    for path in (
        "//*[local-name()='part-name']",
        "//*[local-name()='part-name-display']//*[local-name()='display-text']",
        "//*[local-name()='instrument-name']",
        "//*[local-name()='instrument-sound']",
    ):
        for node in root.xpath(path):
            text = (node.text or "").strip()
            if text:
                tokens.append(text)
    # MIDI program 25 (1-indexed) / 24 (0-indexed) is nylon-string guitar;
    # 26/25 is steel-string. Include them as positive evidence.
    for prog_node in root.xpath("//*[local-name()='midi-program']"):
        try:
            prog = int((prog_node.text or "").strip())
        except ValueError:
            continue
        if prog in (24, 25, 26, 27, 28):
            tokens.append(f"midi-program-{prog}")
    return tokens


def is_guitar(tokens: list[str]) -> bool:
    joined = " ".join(tokens).lower()
    if any(tok in joined for tok in GUITAR_TOKENS):
        return True
    return any(t.startswith("midi-program-") for t in tokens)


def extract_metadata(root: etree._Element) -> dict[str, str]:
    title = find_text(root, "//*[local-name()='work']/*[local-name()='work-title']")
    if not title:
        title = find_text(root, "//*[local-name()='movement-title']")
    opus = find_text(root, "//*[local-name()='work']/*[local-name()='work-number']")
    composer = ""
    creators = root.xpath(
        "//*[local-name()='identification']/*[local-name()='creator']"
    )
    for c in creators:
        ctype = (c.get("type") or "").lower()
        if ctype in ("composer", "") and (c.text or "").strip():
            composer = c.text.strip()
            if ctype == "composer":
                break
    key_fifths = find_text(
        root,
        "//*[local-name()='measure'][1]//*[local-name()='key']/*[local-name()='fifths']",
    )
    return {
        "title": title.strip(),
        "composer": composer.strip(),
        "opus": opus.strip(),
        "key_fifths": key_fifths.strip(),
    }


def count_parts(root: etree._Element) -> int:
    return len(root.xpath("//*[local-name()='part-list']/*[local-name()='score-part']"))


def validate_one(blob: bytes, fmt: str) -> dict[str, Any]:
    """Validate one file. Returns either {ok: True, metadata: …} or
    {ok: False, code: …, detail: …}."""
    if fmt == "mxl":
        extracted = extract_score_xml(blob, fmt)
        if isinstance(extracted, tuple):
            return {"ok": False, "code": "MXL_EXTRACTION_FAILED", "detail": extracted[1]}
        xml_bytes = extracted
    else:
        xml_bytes = blob

    parsed = parse_score(xml_bytes)
    if isinstance(parsed, tuple):
        _, detail = parsed
        code = detail.split(":", 1)[0]
        return {"ok": False, "code": code, "detail": detail}
    root = parsed

    parts = count_parts(root)
    if parts == 0:
        return {"ok": False, "code": "NO_PARTS", "detail": "0 score-part entries"}
    if parts > 1:
        return {"ok": False, "code": "MULTIPLE_PARTS",
                "detail": f"{parts} parts; solo guitar expected"}

    tokens = collect_instrument_tokens(root)
    if not is_guitar(tokens):
        return {"ok": False, "code": "NON_GUITAR_INSTRUMENT",
                "detail": f"tokens={tokens[:6]}"}

    meta = extract_metadata(root)
    if not meta["title"]:
        return {"ok": False, "code": "MISSING_TITLE", "detail": ""}
    if not meta["composer"]:
        return {"ok": False, "code": "MISSING_COMPOSER", "detail": ""}
    if meta["title"].strip().lower() in PLACEHOLDER_TITLES:
        return {"ok": False, "code": "PLACEHOLDER_METADATA",
                "detail": f"title={meta['title']!r}"}
    if meta["composer"].strip().lower() in PLACEHOLDER_COMPOSERS:
        return {"ok": False, "code": "PLACEHOLDER_METADATA",
                "detail": f"composer={meta['composer']!r}"}

    normalized_bytes = etree.tostring(root, xml_declaration=True, encoding="UTF-8")
    return {
        "ok": True,
        "metadata": meta,
        "normalized_bytes": normalized_bytes,
        "normalized_sha256": sha256_bytes(normalized_bytes),
        "parts": parts,
        "instrument_tokens": tokens,
    }


def path_noise_match(candidate_path: str) -> str | None:
    """Return the matching noise token, or None if the path is clean."""
    p = candidate_path.lower()
    for token in PATH_NOISE_TOKENS:
        if token in p:
            return token
    return None


def write_report(stats: Counter, rejections: list[dict[str, Any]],
                 manifest_pieces: list[dict[str, Any]]) -> None:
    total = sum(stats.values())
    lines = [
        "# M1 ingest report",
        "",
        f"- Total files considered: **{total}**",
        f"- Accepted: **{stats['ACCEPTED']}**",
        f"- Rejected: **{total - stats['ACCEPTED']}**",
        "",
        "## Rejections by reason",
        "",
    ]
    reject_counts = Counter(r["code"] for r in rejections)
    if reject_counts:
        for code, n in reject_counts.most_common():
            lines.append(f"- `{code}` — {n}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Top composers in accepted corpus")
    lines.append("")
    composer_counts = Counter(
        (p.get("metadata", {}).get("composer") or "(unknown)")
        for p in manifest_pieces
    )
    for composer, n in composer_counts.most_common(15):
        lines.append(f"- {composer} — {n}")
    if not manifest_pieces:
        lines.append("- (none yet)")

    # Source-repo breakdown — useful for spotting noise sources (ML dumps,
    # OMR test corpora) vs. real curated repertoire repos.
    lines.append("")
    lines.append("## Accepted pieces by source")
    lines.append("")

    def _source_key(p: dict[str, Any]) -> str:
        cid = p.get("candidate_id", "")
        if cid.startswith("gh:"):
            return cid.split("@", 1)[0]
        return cid.split(":", 1)[0] if ":" in cid else cid

    source_counts = Counter(_source_key(p) for p in manifest_pieces)
    for source, n in source_counts.most_common(20):
        lines.append(f"- {source} — {n}")
    if not source_counts:
        lines.append("- (none yet)")

    # Grade coverage — currently populated only by guitarloot. Useful as
    # a sanity check that the curator-assigned grades made it through.
    graded = [p for p in manifest_pieces if p.get("grade")]
    if graded:
        lines.append("")
        lines.append("## Grade coverage (curator-assigned)")
        lines.append("")
        lines.append(f"- Pieces with a grade: **{len(graded)}** / {len(manifest_pieces)}")
        grade_counts = Counter(p["grade"] for p in graded)
        dist_str = ", ".join(
            f"G{g}: {grade_counts[g]}" for g in sorted(grade_counts, key=lambda x: int(x))
        )
        lines.append(f"- Distribution: {dist_str}")
        grade_source_counts = Counter(p.get("grade_source", "") for p in graded)
        for src, n in grade_source_counts.most_common():
            lines.append(f"- Source `{src or '(unset)'}`: {n}")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    ensure_corpus_dirs()

    candidates = {c["candidate_id"]: c for c in load_candidates()}
    fetch_log = read_json(FETCH_LOG_PATH, default={"entries": {}})
    fetch_entries = fetch_log.get("entries", {})

    manifest_pieces: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    seen_sha: dict[str, str] = {}  # sha256 → candidate_id

    stats: Counter[str] = Counter()

    processed = 0
    for cid, entry in fetch_entries.items():
        if args.limit is not None and processed >= args.limit:
            break
        # Container entries (Mutopia parent rows) have no file of their
        # own — every movement underneath them is enumerated as its own
        # entry. Skip the container.
        if entry.get("container") or entry.get("status") == "container":
            continue
        processed += 1
        candidate = candidates.get(cid, {})
        # Synthetic per-movement candidate ids (`...#movementNN`) fall
        # back to the parent for license / page_url metadata.
        if not candidate and "#" in cid:
            parent_cid = cid.split("#", 1)[0]
            candidate = candidates.get(parent_cid, {})

        candidate_path = candidate.get("path") or cid
        noise_token = path_noise_match(candidate_path)
        if noise_token is not None:
            rejections.append({
                "candidate_id": cid,
                "code": "PATH_NOISE",
                "detail": f"matched {noise_token!r}",
            })
            stats["PATH_NOISE"] += 1
            continue

        if entry.get("status") != "ok":
            # Preserve more specific reason codes from the fetch step
            # (e.g. Mutopia LilyPond conversion failures).
            reason = entry.get("reason") or "unknown"
            code = reason if reason in REJECT_CODES else "FETCH_FAILED"
            rejections.append({
                "candidate_id": cid,
                "code": code,
                "detail": (entry.get("detail") or reason)[:240],
            })
            stats[code] += 1
            continue

        raw_path = RAW_DIR / Path(entry["path"]).name
        if not raw_path.exists():
            rejections.append({
                "candidate_id": cid,
                "code": "FETCH_FAILED",
                "detail": f"raw file missing at {raw_path}",
            })
            stats["FETCH_FAILED"] += 1
            continue

        blob = raw_path.read_bytes()
        raw_sha = sha256_bytes(blob)
        if raw_sha in seen_sha:
            rejections.append({
                "candidate_id": cid,
                "code": "DUPLICATE",
                "detail": f"same bytes as {seen_sha[raw_sha]}",
            })
            stats["DUPLICATE"] += 1
            continue

        outcome = validate_one(blob, entry.get("format", "musicxml"))
        if not outcome["ok"]:
            rejections.append({
                "candidate_id": cid,
                "code": outcome["code"],
                "detail": outcome.get("detail", ""),
            })
            stats[outcome["code"]] += 1
            continue

        seen_sha[raw_sha] = cid

        # Filename-safe slug derived from candidate_id (replace path separators).
        safe = cid.replace("/", "_").replace(":", "_").replace("@", "_")
        normalized_path = NORMALIZED_DIR / f"{safe}.musicxml"
        normalized_path.write_bytes(outcome["normalized_bytes"])

        piece = {
            "candidate_id": cid,
            "source": candidate.get("source", "unknown"),
            "page_url": candidate.get("page_url", ""),
            "file_url": candidate.get("file_url", ""),
            "license": candidate.get("license", "unknown"),
            "license_spdx": candidate.get("license_spdx", "unknown"),
            "format": entry.get("format", "musicxml"),
            "raw_sha256": raw_sha,
            "normalized_sha256": outcome["normalized_sha256"],
            "normalized_path": str(normalized_path.relative_to(NORMALIZED_DIR.parent.parent)),
            "metadata": outcome["metadata"],
            "parts": outcome["parts"],
            "instrument_tokens": outcome["instrument_tokens"][:8],
        }
        # Optional curator-assigned grade (currently Guitar Loot only).
        if candidate.get("grade"):
            piece["grade"] = candidate["grade"]
            piece["grade_source"] = candidate.get("grade_source", "")
        manifest_pieces.append(piece)
        stats["ACCEPTED"] += 1

    manifest_pieces.sort(key=lambda p: p["candidate_id"])
    rejections.sort(key=lambda r: (r["code"], r["candidate_id"]))

    write_json_atomic(MANIFEST_PATH, {
        "version": 1,
        "pieces": manifest_pieces,
    })
    write_json_atomic(REJECTED_PATH, {
        "version": 1,
        "rejections": rejections,
    })
    write_report(stats, rejections, manifest_pieces)

    print(f"==> Accepted: {stats['ACCEPTED']}")
    for code, n in sorted(stats.items()):
        if code == "ACCEPTED":
            continue
        print(f"    rejected {code}: {n}")
    print(f"==> Manifest: {MANIFEST_PATH}")
    print(f"==> Rejected: {REJECTED_PATH}")
    print(f"==> Report:   {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
