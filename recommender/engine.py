"""Deterministic title-only rankers. No citation labels or external services."""

import html, json, math, re, unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STOP = set(
    "a an and are as at be by for from in is it of on or that the this to using via we with".split()
)
NOTICE = (
    "Title similarity is not evidence of claim support. Scores are not probabilities."
)


def tokens(text):
    text = unicodedata.normalize(
        "NFKC", html.unescape(re.sub(r"<[^>]*>", " ", text))
    ).casefold()
    return [t for t in re.findall(r"[a-z0-9]{2,}", text) if t not in STOP]


def load_catalog():
    return json.loads((ROOT / "data/catalog.json").read_text(encoding="utf-8"))


def rank(query, candidates, method="jaccard"):
    if method not in ("jaccard", "cosine"):
        raise ValueError("Unknown ranker")
    qt = Counter(tokens(query))
    docs = [(r, Counter(tokens(r["title"]))) for r in candidates]
    if not qt or not docs:
        return []
    df = Counter(t for _, count in docs for t in count)
    idf = {t: 1 + math.log((len(docs) + 1) / (n + 1)) for t, n in df.items()}

    def vector(count):
        v = {t: (1 + math.log(n)) * idf[t] for t, n in count.items() if t in idf}
        norm = math.sqrt(math.fsum(x * x for x in v.values()))
        return {t: w / norm for t, w in v.items()} if norm else {}

    qv = vector(qt) if method == "cosine" else {}
    output = []
    for row, count in docs:
        shared = sorted(set(qt) & set(count))
        if len(shared) < 2:
            continue
        if method == "jaccard":
            size = len(set(qt) | set(count))
            contributions = {t: 1 / size for t in shared}
        else:
            dv = vector(count)
            contributions = {t: qv[t] * dv[t] for t in shared}
        score = round(math.fsum(contributions.values()), 12)
        if score > 0:
            output.append(
                dict(row, score=score, terms=shared, contributions=contributions)
            )
    return sorted(output, key=lambda r: (-r["score"], r["doi"]))


def recommend(
    query, catalog=None, method=None, threshold=None, limit=5, before_year=None
):
    if not isinstance(query, str) or len(query) > 500:
        raise ValueError("Use a title or DOI of at most 500 characters")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("Limit must be an integer from 1 to 20")
    if before_year is not None and (
        type(before_year) != int or not 1800 <= before_year <= 2100
    ):
        raise ValueError("Invalid before_year")
    if method is None or threshold is None:
        config = json.loads(
            (ROOT / "results/selection.json").read_text(encoding="utf-8")
        )
        if method is None:
            method = config["method"]
        if threshold is None:
            threshold = config["threshold"]
    if (
        type(threshold) not in (int, float)
        or not math.isfinite(threshold)
        or not 0 <= threshold <= 1
    ):
        raise ValueError("Threshold must be finite and between zero and one")
    catalog = load_catalog() if catalog is None else catalog
    # Strip labels even when a caller passes a richer local record.
    catalog = [{k: r[k] for k in ["doi", "title", "year", "type"]} for r in catalog]
    lookup = (
        query.strip()
        .lower()
        .removeprefix("https://doi.org/")
        .removeprefix("doi:")
        .strip()
    )
    known = next((r for r in catalog if r["doi"] == lookup), None)
    if known:
        query = known["title"]
        before_year = (
            known["year"] if before_year is None else min(before_year, known["year"])
        )
    candidates = [
        r
        for r in catalog
        if (not known or r["doi"] != known["doi"])
        and (before_year is None or r["year"] < before_year)
    ]
    ranked = rank(query, candidates, method)
    reason = (
        "matched"
        if ranked and ranked[0]["score"] >= threshold
        else ("below-threshold" if ranked else "insufficient-shared-terms")
    )
    return dict(
        query=query,
        known_doi=known["doi"] if known else None,
        before_year=before_year,
        method=method,
        threshold=threshold,
        candidate_count=len(candidates),
        abstained=reason != "matched",
        reason=reason,
        results=ranked[:limit] if reason == "matched" else [],
        notice=NOTICE,
    )
