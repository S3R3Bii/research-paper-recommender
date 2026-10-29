"""Independently rebuild manuscript table values from query-level exports."""

import csv, hashlib, json, re, unicodedata
from fractions import Fraction
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
read = lambda p: json.loads((ROOT / p).read_text(encoding="utf-8"))


def rows(p):
    return list(csv.DictReader((ROOT / p).open(encoding="utf-8", newline="")))


def metrics(data):
    n = len(data)
    a = sum(int(x["answered"]) for x in data)
    h = sum(int(x["hit5"]) for x in data)
    return dict(
        answered=a,
        hits=h,
        hit5_all=Fraction(h, n),
        recall5=sum(
            (Fraction(int(x["hits"]), int(x["positives"])) for x in data), Fraction(0)
        )
        / n,
        mrr5=sum(
            (
                (
                    Fraction(1, int(x["first_hit_rank"]))
                    if int(x["first_hit_rank"])
                    else Fraction(0)
                )
                for x in data
            ),
            Fraction(0),
        )
        / n,
        utility=sum(
            (
                (
                    Fraction(1)
                    if int(x["hit5"])
                    else Fraction(-1, 4) if int(x["answered"]) else Fraction(0)
                )
                for x in data
            ),
            Fraction(0),
        )
        / n,
    )


def main():
    expected = {}
    coverage = rows("results/coverage.csv")
    dev = rows("results/development_queries.csv")
    held = rows("results/held_queries.csv")
    topics = [
        "information retrieval",
        "recommender systems",
        "database query optimization",
        "software defect prediction",
        "graph neural networks",
        "time series forecasting",
        "machine translation",
        "distributed consensus",
    ]
    for i, t in enumerate(topics):
        data = [r for r in coverage if r["stratum"] == t]
        expected[f"coverage-{i}-total"] = (len(data), "d")
        expected[f"coverage-{i}-eligible"] = (
            sum(int(r["evaluable"]) for r in data),
            "d",
        )
    for i, (method, threshold) in enumerate(
        (m, t) for m in ["jaccard", "cosine"] for t in [0, 0.1, 0.2, 0.3, 0.4]
    ):
        m = metrics(
            [
                r
                for r in dev
                if r["method"] == method and float(r["threshold"]) == threshold
            ]
        )
        for key, fmt in [("answered", "d"), ("hits", "d"), ("utility", ".6f")]:
            expected[f"dev-{i}-{key}"] = (
                float(m[key]) if key == "utility" else m[key],
                fmt,
            )
    for i, t in enumerate([0.3, 0]):
        m = metrics([r for r in held if float(r["threshold"]) == t])
        for key in ["answered", "hits", "hit5_all", "recall5", "mrr5", "utility"]:
            expected[f"held-{i}-{key}"] = (
                m[key] if key in ["answered", "hits"] else float(m[key]),
                "d" if key in ["answered", "hits"] else ".6f",
            )
    for i, topic in enumerate(topics[4:]):
        data = [
            r for r in held if float(r["threshold"]) == 0.3 and r["stratum"] == topic
        ]
        m = metrics(data)
        expected[f"stratum-{i}-n"] = (len(data), "d")
        expected[f"stratum-{i}-hits"] = (m["hits"], "d")
        expected[f"stratum-{i}-utility"] = (float(m["utility"]), ".6f")
    values = read("paper/TABLE_VALUES.json")
    assert expected.keys() == values.keys()
    checks = 0
    reader = PdfReader(ROOT / "paper/manuscript.pdf")
    assert len(reader.pages) == 6
    texts = [
        " ".join(unicodedata.normalize("NFKC", p.extract_text()).split())
        for p in reader.pages
    ]
    joined = " ".join(texts)
    for key, (value, fmt) in expected.items():
        assert values[key] == dict(value=value, text=format(value, fmt))
        page = 1 if key.startswith("coverage-") else 2 if key.startswith("dev-") else 3
        assert format(value, fmt) in texts[page]
        checks += 2
    # Check distinctive row values beside each label on the intended page.
    for i, t in enumerate(topics):
        key = f"coverage-{i}"
        pattern = (
            re.escape(t.title())
            + r"\s*"
            + re.escape(values[key + "-total"]["text"])
            + r"\s*"
            + re.escape(values[key + "-eligible"]["text"])
        )
        assert re.search(pattern, texts[1])
        checks += 1
    for needle in [
        "12 of 29",
        "same outcomes",
        "Seventeen answered queries",
        "450 titles",
        "57/263",
        "29/273",
        "no independent human relevance labels",
        "scores",
        "not probabilities",
        "formal-publication projects",
        "34",
        "17 tests",
        "32,518",
        "10,319",
        "four JSON documents",
        "272 SVG coordinate",
        "hypothetical teaching tradeoff",
        "historical availability",
        "unjudged",
        "learner stub",
        "status 2",
        "442 older candidates",
    ]:
        assert needle.casefold() in joined.casefold(), needle
        checks += 1
    assert all(len(t) > 800 for t in texts)
    scope = read("paper/PUBLICATION_SCOPE.json")
    assert (
        len(scope["public_files"]) == 5
        and scope["scope"] == "independent-program-study"
        and scope["formal_submission_target"] is False
    )
    for path, digest in scope["public_files"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
        checks += 1
    assert not reader.get_fields() and "/JavaScript" not in str(
        reader.trailer["/Root"].get("/Names", "")
    )
    root = reader.trailer["/Root"]
    assert "/AA" not in root
    opening = root.get("/OpenAction")
    if opening:
        action = opening.get_object()
        assert isinstance(action, list) and str(action[1]) == "/Fit"
    for page in reader.pages:
        assert "/AA" not in page
        box = page.mediabox
        for ref in page.get("/Annots", []):
            annotation = ref.get_object()
            assert "/AA" not in annotation
            action = annotation.get("/A")
            if action:
                assert action.get_object().get("/S") == "/URI"
            rect = annotation.get("/Rect")
            if rect:
                assert (
                    float(rect[0]) >= float(box.left) - 1
                    and float(rect[1]) >= float(box.bottom) - 1
                    and float(rect[2]) <= float(box.right) + 1
                    and float(rect[3]) <= float(box.top) + 1
                )
            checks += 1
    result = dict(
        status="PASS",
        checks=checks,
        pages=6,
        numerical_table_values=len(expected),
        manuscript_sha256=hashlib.sha256(
            (ROOT / "paper/manuscript.pdf").read_bytes()
        ).hexdigest(),
        pdf_action_scope="No forms, scripts, page/document AA; internal Fit opening and URI references bounded",
        limits="Finite numeric/text/hash checks; visual page inspection recorded in review receipt",
    )
    (ROOT / "results/paper_verification.json").write_bytes(
        (json.dumps(result, indent=2) + "\n").encode()
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
