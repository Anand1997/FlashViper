import pytest
from mqsim.utils.random_generator import RandomGenerator

def test_random_generator_uniform():
    # Use fixed seed for reproducibility
    rg = RandomGenerator(42)
    val = rg.uniform(10.0, 20.0)
    assert 10.0 <= val <= 20.0
    
    # Check if seed works (first call should be consistent)
    rg2 = RandomGenerator(42)
    assert rg2.uniform(10.0, 20.0) == val

def test_random_generator_uint():
    rg = RandomGenerator(123)
    val = rg.uniform_uint(0, 100)
    assert isinstance(val, int)
    assert 0 <= val <= 100
