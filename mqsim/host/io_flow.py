from mqsim.utils.random_generator import RandomGenerator
from mqsim.sim.sim_object import SimObject
from mqsim.sim.engine import Engine

class SyntheticIOFlow(SimObject):
    def __init__(self, id, stream_id, read_ratio, start_lsa, end_lsa, seed, 
                 queue_depth=1, stop_time=0, total_req_count=0, host_interface=None,
                 address_distribution="RANDOM_UNIFORM", hot_ratio=0.1, working_set_ratio=0.8):
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
        
        self.address_distribution = address_distribution
        self.hot_ratio = hot_ratio
        self.working_set_ratio = working_set_ratio
        
        # Calculate working set range
        self.working_set_end_lsa = int(start_lsa + (end_lsa - start_lsa) * working_set_ratio)
        self.hot_region_end_lsa = int(start_lsa + (self.working_set_end_lsa - start_lsa) * hot_ratio)
        
        self.generated_request_count = 0
        self.serviced_request_count = 0
        self.streaming_next_address = start_lsa
        
        # Stats
        self.total_device_response_time = 0

    def generate_next_request(self):
        if (self.stop_time > 0 and Engine().time >= self.stop_time) or \
           (self.total_req_count > 0 and self.generated_request_count >= self.total_req_count):
            return None
            
        # Determine request type
        req_type = "READ" if self.rng.float_random() < self.read_ratio else "WRITE"
        
        # Determine LSA based on distribution
        if self.address_distribution == "RANDOM_UNIFORM":
            lsa = self.rng.uniform_uint(self.start_lsa, self.working_set_end_lsa)
        elif self.address_distribution == "RANDOM_HOTCOLD":
            # 95% of requests to hot region (simplified MQSim default)
            if self.rng.float_random() < 0.95:
                lsa = self.rng.uniform_uint(self.start_lsa, self.hot_region_end_lsa)
            else:
                lsa = self.rng.uniform_uint(self.hot_region_end_lsa + 1, self.working_set_end_lsa)
        elif self.address_distribution == "STREAMING":
            lsa = self.streaming_next_address
            self.streaming_next_address += 8 # size
            if self.streaming_next_address > self.working_set_end_lsa:
                self.streaming_next_address = self.start_lsa
        else:
            lsa = self.rng.uniform_uint(self.start_lsa, self.working_set_end_lsa)
        
        self.generated_request_count += 1
        return {
            'type': req_type,
            'lsa': lsa,
            'size': 8,
            'arrival_time': Engine().time
        }

    def start_simulation(self):
        # Schedule the first execution event at t=1
        Engine().register_sim_event(1, self)

    def execute_sim_event(self, event):
        # Initial burst to fill the queue depth
        # MQSim often starts by filling the whole queue depth regardless of Stop_Time
        for _ in range(self.queue_depth):
            # Bypass Stop_Time check for initial burst
            req = self._generate_request_internal(ignore_stop_time=True)
            if req and self.host_interface:
                self.host_interface.submit_io_request(self.stream_id, req)

    def _generate_request_internal(self, ignore_stop_time=False):
        if not ignore_stop_time and self.stop_time > 0 and Engine().time >= self.stop_time:
            return None
        if self.total_req_count > 0 and self.generated_request_count >= self.total_req_count:
            return None
            
        # Determine request type
        req_type = "READ" if self.rng.float_random() < self.read_ratio else "WRITE"
        
        # Determine LSA based on distribution
        if self.address_distribution == "RANDOM_UNIFORM":
            lsa = self.rng.uniform_uint(self.start_lsa, self.working_set_end_lsa)
        elif self.address_distribution == "RANDOM_HOTCOLD":
            if self.rng.float_random() < 0.95:
                lsa = self.rng.uniform_uint(self.start_lsa, self.hot_region_end_lsa)
            else:
                lsa = self.rng.uniform_uint(self.hot_region_end_lsa + 1, self.working_set_end_lsa)
        elif self.address_distribution == "STREAMING":
            lsa = self.streaming_next_address
            self.streaming_next_address += 8
            if self.streaming_next_address > self.working_set_end_lsa:
                self.streaming_next_address = self.start_lsa
        else:
            lsa = self.rng.uniform_uint(self.start_lsa, self.working_set_end_lsa)
        
        self.generated_request_count += 1
        return {
            'type': req_type,
            'lsa': lsa,
            'size': 8,
            'arrival_time': Engine().time
        }

    def generate_next_request(self):
        return self._generate_request_internal(ignore_stop_time=False)

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
