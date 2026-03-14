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
        
        # MQSim Style Stats
        self.STAT_generated_request_count = 0
        self.STAT_generated_read_request_count = 0
        self.STAT_generated_write_request_count = 0
        self.STAT_serviced_request_count = 0
        self.STAT_serviced_read_request_count = 0
        self.STAT_serviced_write_request_count = 0
        self.STAT_transferred_bytes_total = 0
        self.STAT_transferred_bytes_read = 0
        self.STAT_transferred_bytes_write = 0
        self.STAT_sum_device_response_time = 0
        self.STAT_min_device_response_time = float('inf')
        self.STAT_max_device_response_time = 0
        
        # Stats
        self.total_device_response_time = 0

    def start_simulation(self):
        # Schedule the first execution event at t=1
        Engine().register_sim_event(1, self)

    def execute_sim_event(self, event):
        # Initial burst to fill the queue depth
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
        
        # Update Stats
        self.STAT_generated_request_count += 1
        if req_type == "READ":
            self.STAT_generated_read_request_count += 1
        else:
            self.STAT_generated_write_request_count += 1

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
        delay = completion_time - host_req['arrival_time']
        self.total_device_response_time += delay
        
        # Update MQSim Style Stats
        self.STAT_serviced_request_count += 1
        bytes_transferred = host_req['size'] * 512
        self.STAT_transferred_bytes_total += bytes_transferred
        if host_req['type'] == "READ":
            self.STAT_serviced_read_request_count += 1
            self.STAT_transferred_bytes_read += bytes_transferred
        else:
            self.STAT_serviced_write_request_count += 1
            self.STAT_transferred_bytes_write += bytes_transferred
            
        self.STAT_sum_device_response_time += delay
        self.STAT_min_device_response_time = min(self.STAT_min_device_response_time, delay)
        self.STAT_max_device_response_time = max(self.STAT_max_device_response_time, delay)
        
        # In QUEUE_DEPTH mode, generate a new one to maintain depth
        new_req = self.generate_next_request()
        if new_req and self.host_interface:
            self.host_interface.submit_io_request(self.stream_id, new_req)

    def report_results_in_xml(self, name_prefix, xml_writer):
        xmlwriter = xml_writer # alias
        xmlwriter.write_open_tag("Host.IO_Flow")
        
        xmlwriter.write_attribute_string("Name", self.id)
        xmlwriter.write_attribute_string("Request_Count", self.STAT_generated_request_count)
        xmlwriter.write_attribute_string("Read_Request_Count", self.STAT_generated_read_request_count)
        xmlwriter.write_attribute_string("Write_Request_Count", self.STAT_generated_write_request_count)
        
        sim_time_sec = Engine().time / 1e9
        xmlwriter.write_attribute_string("IOPS", self.STAT_generated_request_count / sim_time_sec if sim_time_sec > 0 else 0)
        xmlwriter.write_attribute_string("IOPS_Read", self.STAT_generated_read_request_count / sim_time_sec if sim_time_sec > 0 else 0)
        xmlwriter.write_attribute_string("IOPS_Write", self.STAT_generated_write_request_count / sim_time_sec if sim_time_sec > 0 else 0)
        
        xmlwriter.write_attribute_string("Bytes_Transferred", float(self.STAT_transferred_bytes_total))
        xmlwriter.write_attribute_string("Bytes_Transferred_Read", float(self.STAT_transferred_bytes_read))
        xmlwriter.write_attribute_string("Bytes_Transferred_Write", float(self.STAT_transferred_bytes_write))
        
        xmlwriter.write_attribute_string("Bandwidth", self.STAT_transferred_bytes_total / sim_time_sec if sim_time_sec > 0 else 0)
        
        avg_lat = (self.STAT_sum_device_response_time / self.STAT_serviced_request_count / 1000) if self.STAT_serviced_request_count > 0 else 0
        xmlwriter.write_attribute_string("Device_Response_Time", int(avg_lat))
        xmlwriter.write_attribute_string("Min_Device_Response_Time", int(self.STAT_min_device_response_time / 1000) if self.STAT_min_device_response_time != float('inf') else 0)
        xmlwriter.write_attribute_string("Max_Device_Response_Time", int(self.STAT_max_device_response_time / 1000))
        
        xmlwriter.write_close_tag()
