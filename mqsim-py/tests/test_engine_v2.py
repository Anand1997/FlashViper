import pytest
from mqsim.sim.engine import Engine
from mqsim.sim.sim_object import SimObject

def test_engine_lifecycle_and_execution():
    engine = Engine()
    engine.reset()
    
    class MockSimObject(SimObject):
        def __init__(self, id):
            super().__init__(id)
            self.validated = False
            self.triggers_setup = False
            self.started = False
            self.events_executed = 0

        def validate_simulation_config(self):
            self.validated = True

        def setup_triggers(self):
            self.triggers_setup = True

        def start_simulation(self):
            self.started = True

        def execute_sim_event(self, event):
            self.events_executed += 1

    obj = MockSimObject("Obj1")
    engine.add_object(obj)
    engine.register_sim_event(100, obj)
    
    engine.start_simulation()
    
    assert obj.validated is True
    assert obj.triggers_setup is True
    assert obj.started is True
    assert obj.events_executed == 1
    assert engine.time == 100
