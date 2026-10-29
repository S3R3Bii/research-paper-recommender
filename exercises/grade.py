"""Grade a locally trusted learner module, never download or execute remote code."""

import importlib.util, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.test_engine import exercise_contract

path = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location("learner", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    checks = exercise_contract(module.rank)
except NotImplementedError:
    print(
        "INCOMPLETE: learner ranker is intentionally a stub; use exercises/reference.py to inspect a working solution."
    )
    sys.exit(2)
print(
    "PASS",
    checks,
    "Jaccard contract assertions; this is not a human-relevance evaluation",
)
