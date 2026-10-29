"""Create three original descriptive figures and retain actual artist geometry."""

import csv, hashlib, json, re
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "svg.fonttype": "none",
        "svg.hashsalt": "paper-recommender-v1",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
GREEN = "#185a43"
ORANGE = "#a64f28"
LIGHT = "#d6dfd1"


def read(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def main():
    output = ROOT / "figures"
    output.mkdir(exist_ok=True)
    manifest = {}
    geometry = []

    def save(fig, name, entries):
        fig.canvas.draw()
        height = fig.get_figheight() * fig.dpi
        for gid, value, artist in entries:
            vertices = artist.get_transform().transform(artist.get_path().vertices[:4])
            points = [
                [float(x * 72 / fig.dpi), float((height - y) * 72 / fig.dpi)]
                for x, y in vertices
            ]
            geometry.append(
                dict(figure=name, gid=gid, value=float(value), points=points)
            )
        for ext in ["pdf", "svg", "png"]:
            p = output / (name + "." + ext)
            fig.savefig(
                p,
                dpi=160,
                metadata={"Creator": "Paper trail study 41"} if ext == "pdf" else None,
            )
            if ext == "svg":
                p.write_bytes(
                    (
                        "\n".join(
                            line.rstrip()
                            for line in p.read_text(encoding="utf-8").splitlines()
                        )
                        + "\n"
                    ).encode()
                )
            manifest[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        plt.close(fig)

    development = read("results/development_metrics.json")
    fig, ax = plt.subplots(figsize=(7.1, 3.3))
    fig.subplots_adjust(left=0.1, right=0.98, bottom=0.19, top=0.86)
    entries = []
    for j, method in enumerate(["jaccard", "cosine"]):
        values = [s["overall"]["utility"] for s in development if s["method"] == method]
        bars = ax.bar(
            [i + (j - 0.5) * 0.34 for i in range(5)],
            values,
            width=0.32,
            color=GREEN if j == 0 else ORANGE,
            label=method.title(),
        )
        for i, (value, bar) in enumerate(zip(values, bars)):
            gid = f"utility-{method}-{i}"
            bar.set_gid(gid)
            entries.append((gid, value, bar))
    ax.set_xticks(range(5), ["0.0", "0.1", "0.2", "0.3", "0.4"])
    ax.set_xlabel("Top-score abstention threshold")
    ax.set_ylabel("Mean hypothetical proxy utility")
    ax.set_ylim(0, 0.45)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    ax.set_title(
        "Ten development candidates · 57 evaluable queries", loc="left", pad=13
    )
    save(fig, "development_search", entries)
    held = read("results/held_metrics.json")
    topics = [
        "graph neural networks",
        "time series forecasting",
        "machine translation",
        "distributed consensus",
    ]
    fig, ax = plt.subplots(figsize=(7.1, 3.4))
    fig.subplots_adjust(left=0.1, right=0.98, bottom=0.26, top=0.85)
    entries = []
    for j, s in enumerate(held):
        values = [s["strata"][t]["hit5_all"] * 100 for t in topics]
        bars = ax.bar(
            [i + (j - 0.5) * 0.34 for i in range(4)],
            values,
            width=0.32,
            color=GREEN if j == 0 else ORANGE,
            label="Selected, threshold 0.3" if j == 0 else "Baseline, threshold 0",
        )
        for i, (v, bar) in enumerate(zip(values, bars)):
            gid = f"held-{j}-{i}"
            bar.set_gid(gid)
            entries.append((gid, v, bar))
    ax.set_xticks(
        range(4),
        [
            "Graph neural\nnetworks (18)",
            "Time series\nforecasting (3)",
            "Machine\ntranslation (6)",
            "Distributed\nconsensus (2)",
        ],
    )
    ax.set_ylim(0, 100)
    ax.set_ylabel("Queries with a deposited reference\nin the top five (%)")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title(
        "Held query strata · identical selected and baseline outcomes",
        loc="left",
        pad=13,
    )
    save(fig, "held_strata", entries)
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
    fig, ax = plt.subplots(figsize=(7.1, 4.3))
    fig.subplots_adjust(left=0.31, right=0.98, bottom=0.30, top=0.85)
    entries = []
    for j, eligible in enumerate([False, True]):
        values = [
            sum(
                r["stratum"] == t and (not eligible or int(r["evaluable"]))
                for r in coverage
            )
            for t in topics
        ]
        bars = ax.barh(
            range(8),
            values,
            color=LIGHT if j == 0 else GREEN,
            label=(
                "Eligible catalog titles"
                if j == 0
                else "With an older in-corpus citation"
            ),
            height=0.68 if j == 0 else 0.36,
        )
        for i, (v, bar) in enumerate(zip(values, bars)):
            gid = f"coverage-{j}-{i}"
            bar.set_gid(gid)
            entries.append((gid, v, bar))
    ax.set_yticks(range(8), [t.title() for t in topics])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Paper queries (count)")
    ax.legend(
        frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.24)
    )
    ax.set_title(
        "Only 86 of 536 catalog titles enter citation scoring", loc="left", pad=13
    )
    save(fig, "corpus_coverage", entries)
    (output / "artist_geometry.json").write_bytes(
        (json.dumps(geometry, indent=2) + "\n").encode()
    )
    (output / "manifest.json").write_bytes(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    )
    print("THREE_FIGURES_CREATED", len(geometry), "BAR_VALUES")


if __name__ == "__main__":
    main()
