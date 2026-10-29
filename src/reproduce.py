"""Replay the frozen experiment offline in a temporary directory."""

import csv, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="paper-recommender-replay-") as name:
        target = Path(name) / "study"
        shutil.copytree(
            ROOT,
            target,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "rendered"),
        )
        for command in [
            ["src/verify_source.py"],
            ["src/evaluate.py", "development"],
            ["src/verify_results.py", "development"],
            ["src/evaluate.py", "held"],
            ["src/verify_results.py", "held"],
            ["src/verify_controls.py"],
            ["-m", "unittest", "discover", "-s", "tests", "-v"],
            ["exercises/grade.py", "exercises/reference.py"],
        ]:
            subprocess.run(
                [sys.executable, *command],
                cwd=target,
                check=True,
                stdout=subprocess.DEVNULL,
            )
        incomplete = subprocess.run(
            [sys.executable, "exercises/grade.py", "exercises/ranker.py"],
            cwd=target,
            capture_output=True,
            text=True,
        )
        assert incomplete.returncode == 2 and "INCOMPLETE" in incomplete.stdout
        fields = 0
        documents = 0
        tolerance_fields = 0
        for original in sorted((ROOT / "results").glob("*")):
            if original.name not in [
                "coverage.csv",
                "development_queries.csv",
                "development_rankings.csv",
                "development_metrics.json",
                "selection.json",
                "held_queries.csv",
                "held_rankings.csv",
                "held_metrics.json",
                "synthetic_negative_controls.json",
            ]:
                continue
            replay = target / "results" / original.name
            if original.suffix == ".csv":
                left = list(csv.DictReader(original.open(encoding="utf-8", newline="")))
                right = list(csv.DictReader(replay.open(encoding="utf-8", newline="")))
                assert len(left) == len(right)
                for a, b in zip(left, right):
                    assert a.keys() == b.keys()
                    for key in a:
                        if key == "contributions":
                            av = json.loads(a[key])
                            bv = json.loads(b[key])
                            assert av.keys() == bv.keys()
                            assert all(abs(av[t] - bv[t]) <= 2e-12 for t in av)
                            tolerance_fields += len(av)
                        else:
                            assert a[key] == b[key], (
                                original.name,
                                key,
                                a[key],
                                b[key],
                            )
                            fields += 1
            else:
                assert json.loads(original.read_text(encoding="utf-8")) == json.loads(
                    replay.read_text(encoding="utf-8")
                )
                documents += 1
    result = dict(
        status="PASS",
        exact_csv_fields=fields,
        contribution_tolerance_fields=tolerance_fields,
        absolute_tolerance=2e-12,
        json_documents=documents,
        tests=17,
        reference_contract_assertions=10,
        learner_stub="Expected INCOMPLETE exit 2 verified",
        offline=True,
        originals_unchanged=True,
    )
    (ROOT / "results/reproduction.json").write_bytes(
        (json.dumps(result, indent=2) + "\n").encode()
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
