from mqsim.ssd.tsu_base import TSUBase

class TSUOutOfOrder(TSUBase):
    def __init__(self, id, channel_count, chip_no_per_channel):
        super().__init__()
        self.id = id
        self.channel_count = channel_count
        self.chip_no_per_channel = chip_no_per_channel
        
        # Initialize 2D arrays of queues: [Channel][Chip]
        self.user_read_queues = [[[] for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        self.user_write_queues = [[[] for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        self.gc_read_queues = [[[] for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        self.gc_write_queues = [[[] for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        self.gc_erase_queues = [[[] for _ in range(chip_no_per_channel)] for _ in range(channel_count)]

    def schedule(self):
        for trans in self.transaction_receive_slots:
            channel_id = trans.address["channel"]
            chip_id = trans.address["chip"]
            
            if trans.type == "READ":
                # Assuming simple user vs GC distinction by some attribute in future
                # For now just user_read
                self.user_read_queues[channel_id][chip_id].append(trans)
            elif trans.type == "WRITE":
                self.user_write_queues[channel_id][chip_id].append(trans)
            elif trans.type == "ERASE":
                self.gc_erase_queues[channel_id][chip_id].append(trans)
                
        self.transaction_receive_slots.clear()

    def service_read_transaction(self, chip): pass
    def service_write_transaction(self, chip): pass
    def service_erase_transaction(self, chip): pass
    def execute_sim_event(self, event): pass
