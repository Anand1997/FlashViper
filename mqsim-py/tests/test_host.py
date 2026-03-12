import pytest
from mqsim.host.io_flow import SyntheticIOFlow

def test_synthetic_flow_generation():
    # Setup flow: 50% reads, uniform random addresses between 0 and 1000
    flow = SyntheticIOFlow(
        read_ratio=0.5,
        start_lsa=0,
        end_lsa=1000,
        seed=42
    )
    
    # Generate 100 requests and check distribution
    requests = [flow.generate_next_request() for _ in range(100)]
    
    reads = [r for r in requests if r['type'] == 'READ']
    writes = [r for r in requests if r['type'] == 'WRITE']
    
    # With seed 42, we expect a roughly 50/50 split
    assert len(reads) > 0
    assert len(writes) > 0
    
    # Check addresses are within range
    for r in requests:
        assert 0 <= r['lsa'] <= 1000
