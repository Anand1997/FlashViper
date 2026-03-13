from mqsim.utils.random_generator import RandomGenerator
from mqsim.sim.sim_object import SimObject
from mqsim.sim.engine import Engine

class SyntheticIOFlow(SimObject):
    def __init__(self, id, stream_id, read_ratio, start_lsa, end_lsa, seed, 
                 queue_depth=1, stop_time=0, total_req_count=0, host_interface=None):
        super().__init__(id)
        self.stream_id = stream_id
        self.read_ratio = read_ratio
        self.start_lsa = start_lsa
        self.end_lsa = end_lsa
        self.queue_depth = queue_depth
        self.stop_time = stop_time
        self.total_req_count = total_req_count
        self.host_interface = host_interface
        self.rng = RandomGenerator(seed)
        
        self.generated_request_count = 0
        self.serviced_request_count = 0
        
        # Stats
        self.total_device_response_time = 0

    def generate_next_request(self):
        if self.stop_time > 0 and Engine().time >= self.stop_time:
            return None
        if self.total_req_count > 0 and self.generated_request_count >= self.total_req_count:
            return None
            
        # Determine request type
        prob = self.rng.float_random()
        req_type = "READ" if prob < self.read_ratio else "WRITE"
        
        # Determine LSA (Uniform)
        lsa = self.rng.uniform_uint(self.start_lsa, self.end_lsa)
        
        self.generated_request_count += 1
        return {
            'type': req_type,
            'lsa': lsa,
            'size': 8, # Fixed size for now
            'arrival_time': Engine().time
        }

    def start_simulation(self):
        # Schedule the first execution event at t=1
        Engine().register_sim_event(1, self)

    def execute_sim_event(self, event):
        # Initial burst to fill the queue depth
        for _ in range(self.queue_depth):
            req = self.generate_next_request()
            if req and self.host_interface:
                self.host_interface.submit_io_request(self.stream_id, req)

    def consume_io_request(self, host_req):
        """
        Called when a request is finished by the SSD.
        """
        self.serviced_request_count += 1
        completion_time = Engine().time
        self.total_device_response_time += (completion_time - host_req['arrival_time'])
        
        # In QUEUE_DEPTH mode, generate a new one to maintain depth
        new_req = self.generate_next_request()
        if new_req and self.host_interface:
            self.host_interface.submit_io_request(self.stream_id, new_req)
