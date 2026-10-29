"""Runnable reference: the same pure ranker used by the working product.

Read recommender/engine.py for the full implementation. Keeping one implementation
prevents the learner answer from silently diverging from the shipped algorithm.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recommender.engine import rank
