import pytest
from mqsim.sim.engine import Engine

def test_engine_event_execution():
    engine = Engine()
    execution_flag = False

    class MockSimObject:
        def execute_sim_event(self, event):
            nonlocal execution_flag
            execution_flag = True

    obj = MockSimObject()
    engine.register_sim_event(100, obj)
    
    assert engine.time == 0
    engine.start_simulation()
    
    assert engine.time == 100
    assert execution_flag is True
