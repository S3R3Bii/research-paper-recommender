# Paper trail · Research paper recommender

Find related research titles, inspect their shared terms, or receive an explicit abstention. This working local product includes a **browser UI, CLI, JSON API, implementation exercise and reference solution**. It is a transparent starting point for reading and a software exercise; human usefulness and time savings have not been measured.

**Measured result:** the selected title-Jaccard threshold of 0.3 recovered a deposited citation in the top five for **12/29 evaluable held queries (41.4%)**, matching the simple baseline. It answered all 29 held queries and abstained on 8/8 authored unrelated controls. Only 86 of 536 catalog titles have older in-corpus references and enter citation scoring. The other 450 titles and all 17 held no-hit queries remain documented. Unlisted suggestions are unjudged, not proven irrelevant.

A similar title does **not** establish claim support, research quality or calibrated confidence. Use this release to run and implement a recommendation system. Obtain independent human relevance judgments and a broader frozen corpus before claiming better discovery or deploying for others.

![The working recommendation interface](assets/product-desktop.png)

## Run the product

Python 3.10 or later is sufficient for the local engine, CLI and API; they use the standard library. From the checkout:

```text
python -m recommender.server
```

Open http://127.0.0.1:18341/ in your browser. Stop the server with Ctrl+C. Searches stay local and are not logged or sent to external services. There is no paid API or personal profile. DOI links open external pages only when you choose them. Known catalog DOIs exclude themselves and restrict recommendations to earlier publication years; free text uses the full corpus unless you set a before-year filter. The retrospective study evaluates only older-year candidates.

```text
python -m recommender "graph neural networks"
python -m recommender "10.1038/s43586-024-00294-7"
```

API: POST /api/recommend with application/json and a body such as {"query":"graph neural networks","limit":5}. Optional before_year is an integer; limit is 1..20, query length at most 500. Same-origin/loopback host checks and fixed routes bound this teaching server; these checks are not a general security certification. Do not expose it as a public service without a separate deployment review.

## Implement it yourself

Follow [EXERCISE.md](EXERCISE.md). The learner file intentionally starts incomplete. The working product always uses the reference implementation.

```text
python exercises/grade.py exercises/ranker.py
python exercises/grade.py exercises/reference.py
python -m unittest discover -s tests -v
```

The stub reports INCOMPLETE with exit 2. The reference passes ten Jaccard contract assertions; 17 product/API tests cover normalization, deterministic ties, labels, abstention, year/DOI exclusions and request boundaries. Passing these finite checks does not validate human relevance.

## Evidence and reproduction

- [Six-page manuscript](paper/manuscript.pdf), [LaTeX](paper/main.tex), [fixed protocol](PROTOCOL.md) and [source rights](DATA_RIGHTS.md).
- [Complete coverage](results/coverage.csv), [all ten development candidates](results/development_metrics.json), [frozen selection](results/selection.json) and [34 frozen dependencies](results/frozen_dependencies.json).
- [Held outcomes by stratum](results/held_metrics.json), [every held query](results/held_queries.csv), [ranked suggestions](results/held_rankings.csv) and [synthetic controls](results/synthetic_negative_controls.json).
- [Source capture receipts](SOURCE_CAPTURE.json), [independent source reconciliation](data/source_verification.json), independent [development](results/independent_development.json) / [held](results/independent_held.json) checks, [offline replay](results/reproduction.json) and [UI inspection](results/ui_verification.json).

```text
python -m pip install -r requirements.txt
python src/reproduce.py
python src/verify_figures.py
python src/verify_paper.py
python src/verify_canonical_git.py
```

The replay is offline and compares the captured minimal public snapshot. Re-running the live Crossref requests may return changed search results. Full raw-source reconciliation requires private originals outside the checkout; public hash/schema checks alone cannot prove those originals. Do not commit those raw responses, full texts, abstracts, personal fields or private manuscripts.

## What this release establishes

The protocol preceded eight bounded Crossref requests; 536 unique journal/proceedings articles passed fixed rules, with 264 exclusions. Independent source reconciliation passed 16,228 checks; independent NumPy/SQL/exact-fraction reconstruction passed 26,812 development and 4,316 held checks. Offline replay matched 32,518 exact CSV fields, 10,319 explanatory contribution values within 2e-12 absolute tolerance, and four JSON documents. Three original figures have 34 source values, 272 SVG coordinate checks and nine hashes; the paper has 70 independently reconstructed table values and 182 checks. All six final pages and desktop/phone interface states were visually inspected.

The methods are established Jaccard and log-TF/IDF cosine; the finite 2x5 grid uses a hypothetical +1/-0.25/0 citation-proxy utility. No embeddings, independent human relevance gold standard, novelty, significance, support verification, historical availability, calibrated confidence, production deployment or realized benefit is claimed. Request strata do not guarantee independent scientific topics; the shared catalog and year-only chronology are disclosed. Independent program manuscripts are public within approved scope; formal-publication projects including Azure optimization remain private.
