from mqsim.sim.sim_object import SimObject
from mqsim.ssd.user_request import UserRequest

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
        self.io_flow = None # Link back to Host IO Flow

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
        self.cache_manager = None # Will be linked later

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

    def set_io_flow(self, stream_id, io_flow):
        self.input_streams[stream_id].io_flow = io_flow

    def submit_io_request(self, stream_id, host_req):
        stream = self.input_streams[stream_id]
        stream.submission_tail = (stream.submission_tail + 1) % stream.submission_queue_size
        
        # Create UserRequest
        user_req = UserRequest(
            stream_id=stream_id,
            type=host_req['type'],
            lsa=host_req['lsa'],
            size_in_sectors=host_req['size']
        )
        # Store original host request info for reporting/timing
        user_req.host_request = host_req
        
        stream.waiting_user_requests.append(user_req)
        stream.on_the_fly_requests += 1
        
        if self.cache_manager:
            self.cache_manager.process_new_user_request(user_req)
            
        return user_req

    def finish_user_request(self, user_req):
        """
        Called by FTL when a user request is finished.
        """
        stream = self.input_streams[user_req.stream_id]
        stream.on_the_fly_requests -= 1
        
        # Notify IO Flow
        if stream.io_flow:
            stream.io_flow.consume_io_request(user_req.host_request)

    def execute_sim_event(self, event):
        pass
