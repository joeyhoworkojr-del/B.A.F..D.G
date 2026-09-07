"""Pinned model version.

Every stored prediction records the version of the model that produced it, so
a later model can never silently recompute (and quietly improve) a prediction
that was already made and is being graded. Bump this whenever the prediction
maths changes in a way that would move stored numbers.
"""
from __future__ import annotations

MODEL_VERSION = "2026.09.1-gridiron"
