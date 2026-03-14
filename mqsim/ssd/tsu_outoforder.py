from mqsim.ssd.tsu_base import TSUBase
from mqsim.utils.signal import Signal
from mqsim.nvm_chip.flash_chip import ChipStatus, DieStatus

class TSUOutOfOrder(TSUBase):
    def __init__(self, id, channel_count, chip_no_per_channel, stream_count=1):
        super().__init__()
        self.id = id
        self.channel_count = channel_count
        self.chip_no_per_channel = chip_no_per_channel
        self.stream_count = stream_count
        
        self.program_suspension_enabled = False
        self.erase_suspension_enabled = False
        
        # User queues: [Channel][Chip][Stream]
        self.user_read_queues = [[[[] for _ in range(stream_count)] for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        self.user_write_queues = [[[[] for _ in range(stream_count)] for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        
        # System queues: [Channel][Chip] (Shared across streams)
        self.gc_read_queues = [[[] for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        self.gc_write_queues = [[[] for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        self.gc_erase_queues = [[[] for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        self.mapping_read_queues = [[[] for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        self.mapping_write_queues = [[[] for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        
        # Track last serviced stream for Round Robin: [Channel][Chip]
        self.last_serviced_stream_read = [[0 for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        self.last_serviced_stream_write = [[0 for _ in range(chip_no_per_channel)] for _ in range(channel_count)]

        # (Chip, Die) -> List of Active Transactions
        self.active_transactions = {}
        # (Chip, Die) -> List of Suspended Transactions
        self.suspended_transactions = {}

        self.on_transaction_finished = Signal()
        self.host_interface = None # To be linked
        self.ftl = None # To be linked

    def schedule(self):
        affected_dies = set()
        for trans in self.transaction_receive_slots:
            channel_id = trans.address["channel"]
            chip_id = trans.address["chip"]
            die_id = trans.address.get("die", 0)
            affected_dies.add((channel_id, chip_id, die_id))
            
            if trans.type == "READ":
                if trans.source == "MAPPING":
                    self.mapping_read_queues[channel_id][chip_id].append(trans)
                elif trans.source == "GC_WL":
                    self.gc_read_queues[channel_id][chip_id].append(trans)
                else:
                    self.user_read_queues[channel_id][chip_id][trans.stream_id].append(trans)
            elif trans.type == "WRITE":
                if trans.source == "MAPPING":
                    self.mapping_write_queues[channel_id][chip_id].append(trans)
                elif trans.source == "GC_WL":
                    self.gc_write_queues[channel_id][chip_id].append(trans)
                else:
                    self.user_write_queues[channel_id][chip_id][trans.stream_id].append(trans)
            elif trans.type == "ERASE":
                self.gc_erase_queues[channel_id][chip_id].append(trans)
                
        self.transaction_receive_slots.clear()
        
        # Trigger servicing for affected dies
        if self.phy:
            for channel_id, chip_id, die_id in affected_dies:
                chip = self.phy.get_chip(channel_id, chip_id)
                self.service_chip_requests(chip, die_id)

    def _find_ready_transactions(self, queues, die_id, max_planes, is_user_queue=False, stream_id_start=0):
        """
        Enhanced to support Round Robin among streams if is_user_queue is True.
        """
        grouped_txs = []
        plane_vector = 0
        target_page_id = None
        
        # If user queue, we need to flatten/interleave based on Round Robin
        queues_to_process = []
        if is_user_queue:
            # Reorder queues based on starting stream_id (Round Robin)
            for i in range(self.stream_count):
                s_id = (stream_id_start + i) % self.stream_count
                queues_to_process.append((queues[s_id], s_id))
        else:
            for q in queues:
                queues_to_process.append((q, -1))

        for queue, s_id in queues_to_process:
            i = 0
            while i < len(queue) and len(grouped_txs) < max_planes:
                tx = queue[i]
                if tx.address.get("die", 0) == die_id and self._transaction_is_ready(tx):
                    plane_id = tx.address.get("plane", 0)
                    page_id = tx.address.get("page", 0)
                    
                    if (plane_vector & (1 << plane_id)) == 0:
                        if target_page_id is None or target_page_id == page_id:
                            target_page_id = page_id
                            plane_vector |= (1 << plane_id)
                            grouped_txs.append(queue.pop(i))
                            # If we found a transaction for a stream, update the last serviced
                            if s_id != -1:
                                channel_id = tx.address["channel"]
                                chip_id = tx.address["chip"]
                                if tx.type == "READ":
                                    self.last_serviced_stream_read[channel_id][chip_id] = (s_id + 1) % self.stream_count
                                else:
                                    self.last_serviced_stream_write[channel_id][chip_id] = (s_id + 1) % self.stream_count
                            continue
                i += 1
            if len(grouped_txs) == max_planes:
                break
                
        return grouped_txs

    def service_read_transaction(self, chip, die_id):
        channel_id = chip.channel_id
        chip_id = chip.chip_id
        
        is_urgent = False
        if self.ftl and self.ftl.gc_and_wl_unit:
            is_urgent = self.ftl.gc_and_wl_unit.is_urgent({
                "channel": channel_id, "chip": chip_id, "die": die_id, "plane": 0
            })

        # 1. High Priority: Mapping
        txs = self._find_ready_transactions([self.mapping_read_queues[channel_id][chip_id]], die_id, chip.dies[die_id].planes_per_die)
        if txs:
            self._issue_command_to_chip(chip, txs, die_id)
            return True

        # 2. GC (if urgent)
        if is_urgent:
            txs = self._find_ready_transactions([self.gc_read_queues[channel_id][chip_id]], die_id, chip.dies[die_id].planes_per_die)
            if txs:
                self._issue_command_to_chip(chip, txs, die_id)
                return True

        # 3. User (Round Robin)
        start_stream = self.last_serviced_stream_read[channel_id][chip_id]
        txs = self._find_ready_transactions(self.user_read_queues[channel_id][chip_id], die_id, chip.dies[die_id].planes_per_die, 
                                           is_user_queue=True, stream_id_start=start_stream)
        if txs:
            self._issue_command_to_chip(chip, txs, die_id)
            return True

        # 4. GC (if not urgent)
        if not is_urgent:
            txs = self._find_ready_transactions([self.gc_read_queues[channel_id][chip_id]], die_id, chip.dies[die_id].planes_per_die)
            if txs:
                self._issue_command_to_chip(chip, txs, die_id)
                return True

        return False

    def service_write_transaction(self, chip, die_id):
        channel_id = chip.channel_id
        chip_id = chip.chip_id
        
        is_urgent = False
        if self.ftl and self.ftl.gc_and_wl_unit:
            is_urgent = self.ftl.gc_and_wl_unit.is_urgent({
                "channel": channel_id, "chip": chip_id, "die": die_id, "plane": 0
            })

        # 1. Mapping
        txs = self._find_ready_transactions([self.mapping_write_queues[channel_id][chip_id]], die_id, chip.dies[die_id].planes_per_die)
        if txs:
            self._issue_command_to_chip(chip, txs, die_id)
            return True

        # 2. GC (if urgent)
        if is_urgent:
            txs = self._find_ready_transactions([self.gc_write_queues[channel_id][chip_id]], die_id, chip.dies[die_id].planes_per_die)
            if txs:
                self._issue_command_to_chip(chip, txs, die_id)
                return True

        # 3. User (Round Robin)
        start_stream = self.last_serviced_stream_write[channel_id][chip_id]
        txs = self._find_ready_transactions(self.user_write_queues[channel_id][chip_id], die_id, chip.dies[die_id].planes_per_die,
                                           is_user_queue=True, stream_id_start=start_stream)
        if txs:
            self._issue_command_to_chip(chip, txs, die_id)
            return True

        # 4. GC (if not urgent)
        if not is_urgent:
            txs = self._find_ready_transactions([self.gc_write_queues[channel_id][chip_id]], die_id, chip.dies[die_id].planes_per_die)
            if txs:
                self._issue_command_to_chip(chip, txs, die_id)
                return True

        return False

    def handle_chip_idle_signal(self, chip, die_id=0):
        # 1. Finish the previous transactions if any
        if (chip, die_id) in self.active_transactions:
            finished_txs = self.active_transactions.pop((chip, die_id))
            
            for finished_tr in finished_txs:
                if finished_tr.source == "MAPPING":
                    if self.ftl:
                        self.ftl.handle_transaction_finished(finished_tr)
                    continue

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
        self.service_chip_requests(chip, die_id)

    def service_chip_requests(self, chip, die_id=0):
        die = chip.dies[die_id]
        if die.status == DieStatus.BUSY:
            # Check if we can suspend for an urgent read
            active_txs = self.active_transactions.get((chip, die_id))
            if not active_txs:
                return
                
            can_suspend = (active_txs[0].type == "WRITE" and self.program_suspension_enabled) or \
                          (active_txs[0].type == "ERASE" and self.erase_suspension_enabled)
            
            if can_suspend:
                # Check for ready READs
                queues = [self.mapping_read_queues[chip.channel_id][chip.chip_id],
                          self.gc_read_queues[chip.channel_id][chip.chip_id]]
                for s_q in self.user_read_queues[chip.channel_id][chip.chip_id]:
                    queues.append(s_q)
                
                if self._any_ready_transaction(queues, die_id):
                    # Suspend current
                    chip.suspend(die_id)
                    self.suspended_transactions[(chip, die_id)] = active_txs
                    # The suspend() call will fire on_idle, which triggers service_chip_requests again
            return

        # Die is IDLE. 
        # First priority: resume suspended transactions if no higher priority reads are waiting
        if (chip, die_id) in self.suspended_transactions:
            queues = [self.mapping_read_queues[chip.channel_id][chip.chip_id],
                      self.gc_read_queues[chip.channel_id][chip.chip_id]]
            for s_q in self.user_read_queues[chip.channel_id][chip.chip_id]:
                queues.append(s_q)
            
            if not self._any_ready_transaction(queues, die_id):
                resumed_txs = self.suspended_transactions.pop((chip, die_id))
                self.active_transactions[(chip, die_id)] = resumed_txs
                chip.resume(die_id)
                return

        # Normal scheduling
        if not self.service_read_transaction(chip, die_id):
            if not self.service_write_transaction(chip, die_id):
                self.service_erase_transaction(chip, die_id)

    def _any_ready_transaction(self, queues, die_id):
        for queue in queues:
            for tx in queue:
                if tx.address.get("die", 0) == die_id and self._transaction_is_ready(tx):
                    return True
        return False

    def service_erase_transaction(self, chip, die_id):
        channel_id = chip.channel_id
        chip_id = chip.chip_id
        
        queues = [self.gc_erase_queues[channel_id][chip_id]]
        txs = self._find_ready_transactions(queues, die_id, chip.dies[die_id].planes_per_die)
        if txs:
            self._issue_command_to_chip(chip, txs, die_id)
            return True
        return False

    def _issue_command_to_chip(self, chip, transactions, die_id):
        self.active_transactions[(chip, die_id)] = transactions
        base_tx = transactions[0]
        
        if base_tx.type == "READ":
            cmd_type = "READ_PAGE_MULTIPLANE" if len(transactions) > 1 else "READ_PAGE"
        elif base_tx.type == "WRITE":
            cmd_type = "PROGRAM_PAGE_MULTIPLANE" if len(transactions) > 1 else "PROGRAM_PAGE"
        else:
            cmd_type = "ERASE_BLOCK_MULTIPLANE" if len(transactions) > 1 else "ERASE_BLOCK"
        
        chip.start_command_execution(cmd_type, die_id, base_tx.address.get("page", 0))

    def execute_sim_event(self, event): pass
