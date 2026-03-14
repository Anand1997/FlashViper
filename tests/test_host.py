import pytest
from mqsim.host.io_flow import SyntheticIOFlow
from mqsim.sim.engine import Engine

class MockHostInterface:
    def __init__(self):
        self.submitted_requests = []
        
    def submit_io_request(self, stream_id, req):
        self.submitted_requests.append(req)

def test_synthetic_flow_generation():
    engine = Engine()
    engine.reset()

    mock_interface = MockHostInterface()
    
    # Setup flow: 50% reads, queue depth of 5
    flow = SyntheticIOFlow(
        id="Flow0",
        stream_id=0,
        read_ratio=0.5,
        start_lsa=0,
        end_lsa=1000,
        seed=42,
        queue_depth=5,
        host_interface=mock_interface
    )
    
    engine.add_object(flow)
    engine.start_simulation()
    
    # Verify that the engine triggered execute_sim_event and generated 5 requests
    assert len(mock_interface.submitted_requests) == 5
    
    reads = [r for r in mock_interface.submitted_requests if r['type'] == 'READ']
    writes = [r for r in mock_interface.submitted_requests if r['type'] == 'WRITE']
    
    # Check that both reads and writes are generated (with seed 42)
    assert len(reads) > 0
    assert len(writes) > 0
    
    # Check addresses are within range
    for r in mock_interface.submitted_requests:
        assert 0 <= r['lsa'] <= 1000
