import math
from typing import Dict


def probability_correct(memory_strength: float, difficulty: float) -> float:
    logit = memory_strength - difficulty
    return 1 / (1 + math.exp(-logit))
