from mqsim.ssd.tsu_base import TSUBase
from mqsim.utils.signal import Signal
from mqsim.nvm_chip.flash_chip import ChipStatus

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
        
        # Chip -> Active Transaction map
        self.active_transactions = {}

        self.on_transaction_finished = Signal()
        self.host_interface = None # To be linked

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

    def handle_chip_idle_signal(self, chip):
        # 1. Finish the previous transaction if any
        if chip in self.active_transactions:
            finished_tr = self.active_transactions.pop(chip)
            
            # Remove from user request's transaction list
            if finished_tr.user_request:
                user_req = finished_tr.user_request
                if finished_tr in user_req.transaction_list:
                    user_req.transaction_list.remove(finished_tr)
                
                # If all transactions for this user request are done, finish it
                if len(user_req.transaction_list) == 0:
                    if self.host_interface:
                        self.host_interface.finish_user_request(user_req)

        # 2. Service the next request
        self.service_chip_requests(chip)

    def service_chip_requests(self, chip):
        if chip.status != ChipStatus.IDLE:
            return
            
        if not self.service_read_transaction(chip):
            if not self.service_write_transaction(chip):
                self.service_erase_transaction(chip)

    def service_read_transaction(self, chip):
        channel_id = chip.channel_id
        chip_id = chip.chip_id
        
        for queue in [self.mapping_read_queues[channel_id][chip_id],
                      self.gc_read_queues[channel_id][chip_id],
                      self.user_read_queues[channel_id][chip_id]]:
            if len(queue) > 0:
                tx = queue.pop(0)
                self._issue_command_to_chip(chip, tx)
                return True
        return False

    def service_write_transaction(self, chip):
        channel_id = chip.channel_id
        chip_id = chip.chip_id
        
        for queue in [self.gc_write_queues[channel_id][chip_id],
                      self.user_write_queues[channel_id][chip_id]]:
            if len(queue) > 0:
                tx = queue.pop(0)
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
        self.active_transactions[chip] = transaction
        cmd_type = "READ_PAGE" if transaction.type == "READ" else "PROGRAM_PAGE"
        if transaction.type == "ERASE": cmd_type = "ERASE_BLOCK"
        
        chip.start_command_execution(cmd_type, transaction.address.get("page", 0))

    def execute_sim_event(self, event): pass
