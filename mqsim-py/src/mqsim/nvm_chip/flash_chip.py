from mqsim.sim.sim_object import SimObject

class FlashChip(SimObject):
    def __init__(self, obj_id, channel_id, local_chip_id, 
                 flash_technology, die_no, planes_per_die,
                 read_latencies, program_latencies, erase_latency):
        super().__init__(obj_id)
        self.channel_id = channel_id
        self.local_chip_id = local_chip_id
        self.flash_technology = flash_technology
        self.die_no = die_no
        self.planes_per_die = planes_per_die
        self.read_latencies = read_latencies
        self.program_latencies = program_latencies
        self.erase_latency = erase_latency

    def get_command_execution_latency(self, command_type, page_id):
        latency_type = 0
        if self.flash_technology == "MLC":
            latency_type = page_id % 2
        elif self.flash_technology == "TLC":
            # Simplified TLC logic from MQSim
            if page_id <= 5:
                latency_type = 0
            elif page_id <= 7:
                latency_type = 1
            else:
                latency_type = ((page_id - 8) >> 1) % 3
        else: # SLC
            latency_type = 0

        if "READ" in command_type:
            return self.read_latencies[latency_type]
        elif "PROGRAM" in command_type:
            return self.program_latencies[latency_type]
        elif "ERASE" in command_type:
            return self.erase_latency
        
        return 0

    def execute_sim_event(self, event):
        # To be implemented when we port event handling
        pass
