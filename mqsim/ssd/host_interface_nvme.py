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
        
        # Buffer for requests that are submitted by host but not yet fetched by SSD
        self.sq_buffer = [] 
        
        self.waiting_user_requests = [] # Requests currently being processed by SSD
        self.completed_user_requests = []
        self.on_the_fly_requests = 0
        self.io_flow = None # Link back to Host IO Flow
        
        self.is_fetching = False

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
        
        # PCIe Latency (simplified MQSim model)
        # Latency = base_delay + (size / bandwidth)
        self.pcie_base_delay = 1000 # 1us
        self.pcie_bandwidth = 1.0 # GB/s per lane (from config)

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
        
        # 1. Check if SQ is full
        sq_occupancy = (stream.submission_tail - stream.submission_head + stream.submission_queue_size) % stream.submission_queue_size
        if sq_occupancy >= stream.submission_queue_size - 1:
            return None # SQ Full

        # 2. Add to SQ and update tail (Host action)
        stream.submission_tail = (stream.submission_tail + 1) % stream.submission_queue_size
        stream.sq_buffer.append(host_req)
        
        # 3. Trigger Fetch if not already fetching
        if not stream.is_fetching:
            self._schedule_fetch(stream_id)
            
        return True

    def _schedule_fetch(self, stream_id):
        stream = self.input_streams[stream_id]
        if not stream.sq_buffer:
            return

        stream.is_fetching = True
        
        # Calculate PCIe delay for fetching a batch
        batch_size = min(len(stream.sq_buffer), self.queue_fetch_size)
        # NVMe command is 64 bytes
        transfer_size = batch_size * 64 
        pcie_delay = self.pcie_base_delay + int(transfer_size / (self.pcie_bandwidth * 1e9 / 1e9)) # Simplified
        
        from mqsim.sim.engine import Engine
        Engine().register_sim_event(Engine().time + pcie_delay, self, 
                                     parameters={"type": "FETCH", "stream_id": stream_id, "batch_size": batch_size})

    def finish_user_request(self, user_req):
        """
        Called by FTL or Cache when a user request is finished.
        """
        if user_req.already_finished:
            return
            
        user_req.already_finished = True
        stream = self.input_streams[user_req.stream_id]
        
        # 1. Check if CQ is full
        cq_occupancy = (stream.completion_tail - stream.completion_head + stream.completion_queue_size) % stream.completion_queue_size
        if cq_occupancy >= stream.completion_queue_size - 1:
            # In real MQSim, it would wait for Head doorbell update. 
            # For now, we assume host always makes room.
            pass

        # 2. Write to CQ (SSD action) with PCIe delay
        # NVMe completion is 16 bytes
        pcie_delay = self.pcie_base_delay + int(16 / (self.pcie_bandwidth * 1e9 / 1e9))
        
        from mqsim.sim.engine import Engine
        Engine().register_sim_event(Engine().time + pcie_delay, self, 
                                     parameters={"type": "COMPLETE", "user_req": user_req})

    def execute_sim_event(self, event):
        params = event.parameters
        if params["type"] == "FETCH":
            stream_id = params["stream_id"]
            batch_size = params["batch_size"]
            stream = self.input_streams[stream_id]
            
            for _ in range(batch_size):
                if not stream.sq_buffer:
                    break
                host_req = stream.sq_buffer.pop(0)
                
                # Create UserRequest
                user_req = UserRequest(
                    stream_id=stream_id,
                    type=host_req['type'],
                    lsa=host_req['lsa'],
                    size_in_sectors=host_req['size']
                )
                user_req.host_request = host_req
                
                stream.on_the_fly_requests += 1
                stream.submission_head = (stream.submission_head + 1) % stream.submission_queue_size
                
                if self.cache_manager:
                    self.cache_manager.process_new_user_request(user_req)
            
            stream.is_fetching = False
            # Check if more are waiting
            if stream.sq_buffer:
                self._schedule_fetch(stream_id)

        elif params["type"] == "COMPLETE":
            user_req = params["user_req"]
            stream = self.input_streams[user_req.stream_id]
            
            stream.on_the_fly_requests -= 1
            stream.completion_tail = (stream.completion_tail + 1) % stream.completion_queue_size
            
            # Notify IO Flow
            if stream.io_flow:
                stream.io_flow.consume_io_request(user_req.host_request)
