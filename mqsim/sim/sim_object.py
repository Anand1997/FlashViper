from abc import ABC, abstractmethod

class SimObject(ABC):
    def __init__(self, id):
        self.id = id

    @abstractmethod
    def execute_sim_event(self, event):
        pass

    def start_simulation(self):
        pass

    def validate_simulation_config(self):
        pass

    def setup_triggers(self):
        pass
