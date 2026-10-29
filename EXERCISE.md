# Implement the ranker

Build the ranking core behind Paper trail. The shipped product already works; the learner workspace is deliberately incomplete.

1. Read PROTOCOL.md, especially the token rules, two-term minimum, score rounding and DOI tie break. Inspect data/catalog.json; citation labels must never be ranking features.
2. Implement rank(query, candidates, method='jaccard') in exercises/ranker.py. Return copied candidate dictionaries with score, alphabetically sorted terms and per-term contributions. Use set intersection / union, require two shared tokens, round scores to 12 decimals, and sort descending by score then ascending by DOI. Empty and unseen queries return an empty list; never mutate inputs.
3. Run `python exercises/grade.py exercises/ranker.py`. The initial stub exits 2 with INCOMPLETE. This is expected and is not a passing implementation. The grader checks ten contract assertions; passing them establishes that finite contract only.
4. Run `python exercises/grade.py exercises/reference.py` and inspect recommender/engine.py for the complete reference implementation. It is the production pure ranker, not a second divergent answer.
5. Extend your ranker with log-TF/IDF cosine, query-level abstention and older-year filtering. Explain why a score is not a probability and why deposited references do not make unlisted papers irrelevant. Run `python -m unittest discover -s tests -v` for the product boundaries.

The default product always uses the frozen reference implementation. A learner module is executed only when you explicitly pass its local path to the grader. Do not run untrusted downloaded modules. Changing an exercise answer does not alter the published research results. A new model comparison needs a new protected evaluation, not a retuned old test set.

## Suggested review discussion

What breaks for synonyms or non-English titles? Which papers are excluded by the older-year rule? Why does a citation-recovery miss differ from a human relevance error? When would you collect independent user judgments? Name a baseline and the checks you would require before deploying recommendations to other people.
