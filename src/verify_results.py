"""Rebuild rankings using NumPy arrays and metrics with exact fractions.

This checker does not import the engine or evaluation helpers.
"""

import argparse, csv, hashlib, html, json, re, sqlite3, unicodedata
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STOP = frozenset(
    "a an and are as at be by for from in is it of on or that the this to using via we with".split()
)


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def rows(name):
    return list(csv.DictReader((ROOT / name).open(encoding="utf-8", newline="")))


def tokenize(s):
    s = html.unescape(re.sub("<[^>]*>", " ", s))
    s = unicodedata.normalize("NFKC", s).casefold()
    return Counter(t for t in re.findall("[a-z0-9]{2,}", s) if t not in STOP)


def rebuild_indexes(catalog):
    out = {}
    for year in sorted({r["year"] for r in catalog}):
        docs = [r for r in catalog if r["year"] < year]
        counts = [tokenize(r["title"]) for r in docs]
        vocab = sorted(set().union(*(c.keys() for c in counts))) if counts else []
        column = {t: i for i, t in enumerate(vocab)}
        matrix = np.zeros((len(docs), len(vocab)))
        for i, c in enumerate(counts):
            for t, n in c.items():
                matrix[i, column[t]] = 1 + np.log(n)
        df = (matrix > 0).sum(axis=0)
        idf = 1 + np.log((len(docs) + 1) / (df + 1))
        matrix *= idf
        norm = np.linalg.norm(matrix, axis=1)
        matrix /= np.where(norm > 0, norm, 1)[:, None]
        out[year] = (docs, counts, column, idf, matrix)
    return out


def rank_independent(title, index, method):
    docs, counts, column, idf, matrix = index
    q = tokenize(title)
    if method == "cosine":
        vector = np.zeros(len(column))
        for t, n in q.items():
            if t in column:
                vector[column[t]] = (1 + np.log(n)) * idf[column[t]]
        norm = np.linalg.norm(vector)
        if norm:
            vector /= norm
        similarities = matrix @ vector
    result = []
    for i, (doc, c) in enumerate(zip(docs, counts)):
        common = sorted(q.keys() & c.keys())
        if len(common) < 2:
            continue
        score = (
            len(common) / len(q.keys() | c.keys())
            if method == "jaccard"
            else float(similarities[i])
        )
        if round(score, 12) > 0:
            result.append((round(score, 12), doc["doi"], common))
    return sorted(result, key=lambda r: (-r[0], r[1]))


def exact_metrics(subset):
    n = len(subset)
    answered = sum(int(r["answered"]) for r in subset)
    hits = sum(int(r["hit5"]) for r in subset)
    values = {
        "coverage": Fraction(answered, n),
        "hit5_all": Fraction(hits, n),
        "hit5_answered": Fraction(hits, answered) if answered else Fraction(0),
        "recall5": sum(
            (Fraction(int(r["hits"]), int(r["positives"])) for r in subset), Fraction(0)
        )
        / n,
        "mrr5": sum(
            (
                (
                    Fraction(1, int(r["first_hit_rank"]))
                    if int(r["first_hit_rank"])
                    else Fraction(0)
                )
                for r in subset
            ),
            Fraction(0),
        )
        / n,
        "utility": sum(
            (
                (
                    Fraction(1)
                    if int(r["hit5"])
                    else Fraction(-1, 4) if int(r["answered"]) else Fraction(0)
                )
                for r in subset
            ),
            Fraction(0),
        )
        / n,
    }
    return n, answered, hits, values


def verify(stage):
    catalog = read("data/catalog.json")
    meta = {r["doi"]: r for r in read("data/query_metadata.json")}
    labels = read("data/citation_labels.json")
    indexes = rebuild_indexes(catalog)
    data = rows("results/" + stage + "_queries.csv")
    pred = rows("results/" + stage + "_rankings.csv")
    checks = 0
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE papers(doi TEXT PRIMARY KEY,year INT,part TEXT)")
    db.executemany(
        "INSERT INTO papers VALUES (?,?,?)",
        [(d, r["year"], r["partition"]) for d, r in meta.items()],
    )
    db.execute("CREATE TABLE refs(q TEXT,d TEXT,PRIMARY KEY(q,d))")
    db.executemany(
        "INSERT INTO refs VALUES (?,?)",
        [(q, d) for q, refs in labels.items() for d in refs],
    )
    independent_coverage = {
        d: (c, p)
        for d, c, p in db.execute(
            "SELECT q.doi,(SELECT COUNT(*) FROM papers c WHERE c.year<q.year),(SELECT COUNT(*) FROM refs r JOIN papers c ON c.doi=r.d WHERE r.q=q.doi AND c.year<q.year) FROM papers q"
        )
    }
    for r in rows("results/coverage.csv"):
        c, p = independent_coverage[r["doi"]]
        assert (
            int(r["candidate_count"]),
            int(r["in_corpus_older_references"]),
            int(r["evaluable"]),
        ) == (c, p, int(p > 0))
        checks += 3
    expected_ids = {
        d
        for d, (c, p) in independent_coverage.items()
        if p and meta[d]["partition"] == stage
    }
    assert len(expected_ids) >= 10
    assert {r["doi"] for r in data} == expected_ids
    grouped = defaultdict(list)
    for p in pred:
        grouped[(p["config"], p["query_doi"])].append(p)
    cache = {}
    for r in data:
        q = meta[r["doi"]]
        assert q["partition"] == stage and q["stratum"] == r["stratum"]
        key = (r["doi"], r["method"])
        if key not in cache:
            cache[key] = rank_independent(q["title"], indexes[q["year"]], r["method"])
        ordered = cache[key]
        top = ordered[0][0] if ordered else 0
        answer = int(bool(ordered) and top >= float(r["threshold"]))
        chosen = ordered[:5] if answer else []
        positive = set(labels[q["doi"]]) & {
            x["doi"] for x in catalog if x["year"] < q["year"]
        }
        hit_ranks = [i for i, x in enumerate(chosen, 1) if x[1] in positive]
        assert (
            int(r["positives"]),
            int(r["answered"]),
            int(r["hits"]),
            int(r["hit5"]),
            int(r["first_hit_rank"]),
        ) == (
            len(positive),
            answer,
            len(hit_ranks),
            int(bool(hit_ranks)),
            min(hit_ranks) if hit_ranks else 0,
        )
        assert abs(float(r["top_score"]) - top) <= 2e-12
        checks += 8
        actual = sorted(grouped[(r["config"], r["doi"])], key=lambda p: int(p["rank"]))
        assert len(actual) == len(chosen)
        checks += 1
        for i, (got, want) in enumerate(zip(actual, chosen), 1):
            assert (
                got["candidate_doi"] == want[1]
                and int(got["rank"]) == i
                and abs(float(got["score"]) - want[0]) <= 2e-12
            )
            assert json.loads(got["terms"]) == want[2] and int(
                got["is_deposited_reference"]
            ) == int(want[1] in positive)
            assert (
                abs(
                    sum(json.loads(got["contributions"]).values()) - float(got["score"])
                )
                <= 2e-12
            )
            assert (
                meta[got["candidate_doi"]]["year"] < q["year"]
                and got["candidate_doi"] != r["doi"]
            )
            checks += 7
    summaries = read("results/" + stage + "_metrics.json")
    for s in summaries:
        selected = [
            r
            for r in data
            if r["method"] == s["method"] and float(r["threshold"]) == s["threshold"]
        ]
        assert len(selected) == len(expected_ids) and len(
            {r["doi"] for r in selected}
        ) == len(selected)
        for scope, summary in [("all", s["overall"]), *s["strata"].items()]:
            subset = (
                selected
                if scope == "all"
                else [r for r in selected if r["stratum"] == scope]
            )
            n, a, h, values = exact_metrics(subset)
            assert (n, a, h) == (
                summary["queries"],
                summary["answered"],
                summary["hits"],
            )
            for k, v in values.items():
                assert str(v) == summary["exact"][k] and float(v) == summary[k]
            checks += 15
    if stage == "development":
        assert len(summaries) == 10
        chosen = sorted(
            summaries,
            key=lambda s: (
                -Fraction(s["overall"]["exact"]["utility"]),
                s["threshold"],
                s["method"] != "jaccard",
            ),
        )[0]
        sel = read("results/selection.json")
        assert (sel["method"], sel["threshold"], sel["exact_utility"]) == (
            chosen["method"],
            chosen["threshold"],
            chosen["overall"]["exact"]["utility"],
        )
        checks += 4
    else:
        frozen = read("results/frozen_dependencies.json")
        for path, digest in frozen["sha256"].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
            checks += 1
    result = dict(
        status="PASS",
        stage=stage,
        checks=checks,
        queries=len(expected_ids),
        query_rows=len(data),
        recommendation_rows=len(pred),
        ranking_reconstruction="Independent NumPy, SQL older-year/citation joins and exact metric fractions",
        score_absolute_tolerance=2e-12,
        claim_limit="Citation proxy only; no independent human relevance or claim-support gold standard",
    )
    p = ROOT / "results" / ("independent_" + stage + ".json")
    p.write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps(result))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["development", "held"])
    verify(p.parse_args().stage)
