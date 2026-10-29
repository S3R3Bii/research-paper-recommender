import csv, hashlib, json, re, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
read = lambda p: json.loads((ROOT / p).read_text(encoding="utf-8"))


def main():
    expected = {}
    development = read("results/development_metrics.json")
    for method in ["jaccard", "cosine"]:
        for i, s in enumerate(s for s in development if s["method"] == method):
            expected["utility-" + method + "-" + str(i)] = s["overall"]["utility"]
    topics = [
        "graph neural networks",
        "time series forecasting",
        "machine translation",
        "distributed consensus",
    ]
    for j, s in enumerate(read("results/held_metrics.json")):
        for i, t in enumerate(topics):
            expected[f"held-{j}-{i}"] = 100 * s["strata"][t]["hit5_all"]
    coverage = list(
        csv.DictReader((ROOT / "results/coverage.csv").open(encoding="utf-8"))
    )
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
    for j in [0, 1]:
        for i, t in enumerate(topics):
            expected[f"coverage-{j}-{i}"] = sum(
                r["stratum"] == t and (not j or int(r["evaluable"])) for r in coverage
            )
    geometries = read("figures/artist_geometry.json")
    assert len(geometries) == len(expected) == 34
    checks = 0
    trees = {}
    for record in geometries:
        assert record["value"] == expected[record["gid"]]
        checks += 1
        name = record["figure"]
        if name not in trees:
            trees[name] = ET.parse(ROOT / "figures" / (name + ".svg"))
        group = trees[name].find('.//*[@id="' + record["gid"] + '"]')
        assert group is not None
        path = group.find("{http://www.w3.org/2000/svg}path")
        values = [
            float(n)
            for n in re.findall(
                r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", path.attrib["d"]
            )
        ]
        assert len(values) >= 8
        for got, want in zip(
            values[:8], [v for point in record["points"] for v in point]
        ):
            assert abs(got - want) < 1e-5
            checks += 1
    for name, digest in read("figures/manifest.json").items():
        assert (
            hashlib.sha256((ROOT / "figures" / name).read_bytes()).hexdigest() == digest
        )
        checks += 1
    result = dict(
        status="PASS",
        checks=checks,
        source_values=34,
        svg_coordinates=272,
        figure_hashes=9,
        limits="Finite source-value and rendered-geometry/hash checks; aesthetic review recorded separately",
    )
    (ROOT / "results/figure_verification.json").write_bytes(
        (json.dumps(result, indent=2) + "\n").encode()
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
