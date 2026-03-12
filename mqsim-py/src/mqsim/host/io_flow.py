from mqsim.utils.random_generator import RandomGenerator
from mqsim.sim.sim_object import SimObject
from mqsim.sim.engine import Engine

class SyntheticIOFlow(SimObject):
    def __init__(self, id, read_ratio, start_lsa, end_lsa, seed, queue_depth=1, host_interface=None):
        super().__init__(id)
        self.read_ratio = read_ratio
        self.start_lsa = start_lsa
        self.end_lsa = end_lsa
        self.queue_depth = queue_depth
        self.host_interface = host_interface
        self.rng = RandomGenerator(seed)

    def generate_next_request(self):
        # Determine request type
        prob = self.rng.float_random()
        req_type = "READ" if prob < self.read_ratio else "WRITE"
        
        # Determine LSA (Uniform)
        lsa = self.rng.uniform_uint(self.start_lsa, self.end_lsa)
        
        return {
            'type': req_type,
            'lsa': lsa,
            'size': 8 # Fixed size for now (matching workload.xml default)
        }

    def start_simulation(self):
        # Schedule the first execution event at t=1
        Engine().register_sim_event(1, self)

    def execute_sim_event(self, event):
        # Generate initial requests to fill the queue depth
        for _ in range(self.queue_depth):
            req = self.generate_next_request()
            if self.host_interface:
                # In a full implementation, we'd submit this to the Host Interface.
                # For now, we mock the submission or just print it.
                self.host_interface.submit_io_request(req)
