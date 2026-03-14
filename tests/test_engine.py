import pytest
from mqsim.sim.engine import Engine

def test_engine_event_execution():
    engine = Engine()
    engine.reset()
    execution_flag = False

    class MockSimObject:
        def __init__(self, id):
            self.id = id
        def execute_sim_event(self, event):
            nonlocal execution_flag
            execution_flag = True
        def validate_simulation_config(self): pass
        def setup_triggers(self): pass
        def start_simulation(self): pass

    obj = MockSimObject("Mock")
    engine.register_sim_event(100, obj)
    
    assert engine.time == 0
    engine.start_simulation()
    
    assert engine.time == 100
    assert execution_flag is True
