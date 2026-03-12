from mqsim.sim.sim_object import SimObject

class InputStreamNVMe:
    def __init__(self, priority_class, start_lsa, end_lsa,
                 submission_queue_base_address, submission_queue_size,
                 completion_queue_base_address, completion_queue_size):
        self.priority_class = priority_class
        self.start_lsa = start_lsa
        self.end_lsa = end_lsa
        self.submission_queue_base_address = submission_queue_base_address
        self.submission_queue_size = submission_queue_size
        self.completion_queue_base_address = completion_queue_base_address
        self.completion_queue_size = completion_queue_size
        
        self.submission_head = 0
        self.submission_tail = 0
        self.completion_head = 0
        self.completion_tail = 0
        
        self.waiting_user_requests = []
        self.completed_user_requests = []
        self.on_the_fly_requests = 0

class HostInterfaceNVMe(SimObject):
    def __init__(self, id, max_lsa, submission_queue_depth, completion_queue_depth,
                 no_of_input_streams, queue_fetch_size, sectors_per_page):
        super().__init__(id)
        self.max_lsa = max_lsa
        self.submission_queue_depth = submission_queue_depth
        self.completion_queue_depth = completion_queue_depth
        self.no_of_input_streams = no_of_input_streams
        self.queue_fetch_size = queue_fetch_size
        self.sectors_per_page = sectors_per_page
        
        self.input_streams = []

    def create_new_stream(self, priority_class, start_lsa, end_lsa,
                          submission_queue_base_address, completion_queue_base_address):
        stream_id = len(self.input_streams)
        if stream_id >= self.no_of_input_streams:
            raise RuntimeError("Maximum number of NVMe streams reached!")
            
        stream = InputStreamNVMe(
            priority_class, start_lsa, end_lsa,
            submission_queue_base_address, self.submission_queue_depth,
            completion_queue_base_address, self.completion_queue_depth
        )
        self.input_streams.append(stream)
        return stream_id

    def execute_sim_event(self, event):
        pass
