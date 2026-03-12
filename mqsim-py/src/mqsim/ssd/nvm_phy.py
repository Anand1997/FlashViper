from mqsim.sim.sim_object import SimObject
from mqsim.nvm_chip.flash_chip import FlashChip

class NVMPhy(SimObject):
    def __init__(self, id, channel_count, chip_no_per_channel, 
                 flash_technology, die_no, plane_no,
                 read_latencies, program_latencies, erase_latency,
                 tsu=None):
        super().__init__(id)
        
        self.channels = []
        self.tsu = tsu
        # Initialize physical chips
        self.chips = [[None for _ in range(chip_no_per_channel)] for _ in range(channel_count)]
        
        for c in range(channel_count):
            for i in range(chip_no_per_channel):
                chip_id = f"{id}.Chip.{c}.{i}"
                chip = FlashChip(
                    chip_id, c, i, flash_technology, die_no, plane_no,
                    read_latencies, program_latencies, erase_latency
                )
                self.chips[c][i] = chip
                
                # Automatically connect TSU to chip signals if TSU is provided
                if self.tsu:
                    chip.on_idle.connect(self.tsu.service_chip_requests)

    def get_chip(self, channel_id, chip_id):
        return self.chips[channel_id][chip_id]

    def execute_sim_event(self, event):
        pass
        
    def send_command_to_chip(self, transaction):
        channel_id = transaction.address["channel"]
        chip_id = transaction.address["chip"]
        chip = self.get_chip(channel_id, chip_id)
        
        # Determine command type
        cmd_type = "READ_PAGE" if transaction.type == "READ" else "PROGRAM_PAGE"
        if transaction.type == "ERASE": cmd_type = "ERASE_BLOCK"
        
        chip.start_command_execution(cmd_type, transaction.address.get("page", 0))
