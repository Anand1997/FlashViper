import random
import math

class RandomGenerator:
    def __init__(self, seed):
        self.seed = seed
        self._rng = random.Random(seed)

    def uniform(self, a, b):
        return self._rng.uniform(a, b)

    def uniform_uint(self, m, n):
        return self._rng.randint(m, n)

    def exponential(self, mean):
        # Python's expovariate takes 1/mean
        return self._rng.expovariate(1.0 / mean)

    def normal(self, mean, stddev):
        return self._rng.gauss(mean, stddev)

    def get_uint(self, max_value):
        return self._rng.randint(0, max_value)

    def get_int(self, max_value):
        return self._rng.randint(0, max_value)

    def float_random(self):
        return self._rng.random()
