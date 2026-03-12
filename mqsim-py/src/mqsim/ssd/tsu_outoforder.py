from mqsim.ssd.tsu_base import TSUBase
from mqsim.utils.signal import Signal

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
        self.mapping_read_queues = [[[] for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        
        self.on_transaction_finished = Signal()

    def schedule(self):
        for trans in self.transaction_receive_slots:
            channel_id = trans.address["channel"]
            chip_id = trans.address["chip"]
            
            if trans.type == "READ":
                if trans.source == "MAPPING":
                    self.mapping_read_queues[channel_id][chip_id].append(trans)
                elif trans.source == "GC_WL":
                    self.gc_read_queues[channel_id][chip_id].append(trans)
                else:
                    self.user_read_queues[channel_id][chip_id].append(trans)
            elif trans.type == "WRITE":
                if trans.source == "GC_WL":
                    self.gc_write_queues[channel_id][chip_id].append(trans)
                else:
                    self.user_write_queues[channel_id][chip_id].append(trans)
            elif trans.type == "ERASE":
                self.gc_erase_queues[channel_id][chip_id].append(trans)
                
        self.transaction_receive_slots.clear()

    def service_chip_requests(self, chip):
        """
        Attempt to service the next transaction for the given chip.
        Prioritizes: READ > WRITE > ERASE (with sub-priorities for Mapping/GC)
        """
        if not self.service_read_transaction(chip):
            if not self.service_write_transaction(chip):
                self.service_erase_transaction(chip)

    def service_read_transaction(self, chip):
        channel_id = chip.channel_id
        chip_id = chip.chip_id
        
        # Priority 1: MAPPING
        if len(self.mapping_read_queues[channel_id][chip_id]) > 0:
            tx = self.mapping_read_queues[channel_id][chip_id].pop(0)
            self._issue_command_to_chip(chip, tx)
            return True
            
        # Priority 2: GC
        if len(self.gc_read_queues[channel_id][chip_id]) > 0:
            tx = self.gc_read_queues[channel_id][chip_id].pop(0)
            self._issue_command_to_chip(chip, tx)
            return True
            
        # Priority 3: USERIO
        if len(self.user_read_queues[channel_id][chip_id]) > 0:
            tx = self.user_read_queues[channel_id][chip_id].pop(0)
            self._issue_command_to_chip(chip, tx)
            return True
            
        return False

    def service_write_transaction(self, chip):
        channel_id = chip.channel_id
        chip_id = chip.chip_id
        
        if len(self.gc_write_queues[channel_id][chip_id]) > 0:
            tx = self.gc_write_queues[channel_id][chip_id].pop(0)
            self._issue_command_to_chip(chip, tx)
            return True
            
        if len(self.user_write_queues[channel_id][chip_id]) > 0:
            tx = self.user_write_queues[channel_id][chip_id].pop(0)
            self._issue_command_to_chip(chip, tx)
            return True
            
        return False

    def service_erase_transaction(self, chip):
        channel_id = chip.channel_id
        chip_id = chip.chip_id
        
        if len(self.gc_erase_queues[channel_id][chip_id]) > 0:
            tx = self.gc_erase_queues[channel_id][chip_id].pop(0)
            self._issue_command_to_chip(chip, tx)
            return True
            
        return False

    def _issue_command_to_chip(self, chip, transaction):
        # Notify chip to start execution
        cmd_type = "READ_PAGE" if transaction.type == "READ" else "PROGRAM_PAGE"
        if transaction.type == "ERASE": cmd_type = "ERASE_BLOCK"
        
        chip.start_command_execution(cmd_type, transaction.address.get("page", 0))

    def execute_sim_event(self, event): pass
