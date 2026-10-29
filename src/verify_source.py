"""Independent original-to-projection reconciliation, plus portable hash checks."""

import argparse, hashlib, html, json, re, sqlite3, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--private-root", type=Path)
    a = p.parse_args()
    manifest = read("data/source_manifest.json")
    checks = 0
    for name, digest in manifest["projection_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
        checks += 1
    features = read("data/catalog.json")
    meta = read("data/query_metadata.json")
    labels = read("data/citation_labels.json")
    assert len(features) == len(meta) == len(labels) == manifest["unique_eligible"]
    assert len({r["doi"] for r in features}) == len(features)
    assert all(set(r) == {"doi", "title", "year", "type"} for r in features)
    assert [
        {k: r[k] for k in ["doi", "title", "year", "type"]} for r in meta
    ] == features
    assert (
        len(read("data/source_duplicates.json")) == manifest["duplicates"]
        and len(read("data/source_exclusions.json")) == manifest["exclusions"]
    )
    checks += 5
    mode = "PUBLIC_PROJECTION_HASH_AND_SCHEMA_ONLY"
    if a.private_root:
        expected = {}
        edges = {}
        exclusions = 0
        duplicates = 0
        for index, request in enumerate(manifest["requests"]):
            raw = (a.private_root / f"request-{index}.json").read_bytes()
            assert hashlib.sha256(raw).hexdigest() == request["sha256"]
            items = json.loads(raw)["message"]["items"]
            assert len(items) == request["rows"]
            checks += 2
            for rank, x in enumerate(items, 1):
                d = x.get("DOI", "").strip().casefold()
                text = (x.get("title") or [""])[0]
                text = re.sub("<[^>]*>", " ", text)
                text = " ".join(
                    unicodedata.normalize("NFKC", html.unescape(text)).split()
                )
                year = (x.get("published", {}).get("date-parts") or [[None]])[0][0]
                kind = x.get("type")
                if (
                    not re.fullmatch(r"10\.\d{4,9}/\S+", d)
                    or not text
                    or type(year) != int
                    or year < 2018
                    or year > 2024
                    or kind not in ("journal-article", "proceedings-article")
                ):
                    exclusions += 1
                    continue
                if d in expected:
                    duplicates += 1
                else:
                    expected[d] = {
                        "doi": d,
                        "title": text,
                        "year": year,
                        "type": kind,
                        "stratum": request["topic"],
                        "partition": "development" if index < 4 else "held",
                        "request_rank": rank,
                    }
                edges.setdefault(d, set())
                for ref in x.get("reference", []):
                    v = ref.get("DOI")
                    if isinstance(v, str) and re.fullmatch(
                        r"10\.\d{4,9}/\S+", v.strip().casefold()
                    ):
                        edges[d].add(v.strip().casefold())
        assert meta == [expected[d] for d in sorted(expected)]
        assert labels == {d: sorted(edges[d]) for d in sorted(edges)}
        assert (
            exclusions == manifest["exclusions"]
            and duplicates == manifest["duplicates"]
        )
        checks += len(meta) * 7 + sum(len(v) for v in labels.values()) + 2
        mode = "PRIVATE_ORIGINALS_INDEPENDENTLY_RECONCILED"
    db = sqlite3.connect(":memory:")
    db.execute(
        "CREATE TABLE papers(doi TEXT PRIMARY KEY, year INT, partition TEXT, stratum TEXT)"
    )
    db.executemany(
        "INSERT INTO papers VALUES (?,?,?,?)",
        [(r["doi"], r["year"], r["partition"], r["stratum"]) for r in meta],
    )
    counts = db.execute(
        "SELECT partition,COUNT(*) FROM papers GROUP BY partition"
    ).fetchall()
    assert sum(r[1] for r in counts) == len(features)
    checks += 1
    result = dict(
        status="PASS",
        mode=mode,
        checks=checks,
        records=len(features),
        partitions=dict(counts),
        limitations="Current deposit metadata; no historical availability, relevance or claim-support verification",
    )
    if a.private_root:
        (ROOT / "data/source_verification.json").write_bytes(
            (json.dumps(result, indent=2) + "\n").encode()
        )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
