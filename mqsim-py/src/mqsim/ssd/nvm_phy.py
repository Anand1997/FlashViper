from mqsim.sim.sim_object import SimObject
from mqsim.nvm_chip.flash_chip import FlashChip

class NVMPhy(SimObject):
    def __init__(self, id, channel_count, chip_no_per_channel, 
                 flash_technology, die_no, plane_no,
                 read_latencies, program_latencies, erase_latency, tsu,
                 suspend_program_latency=0, suspend_erase_latency=0):
        super().__init__(id)
        self.channel_count = channel_count
        self.chip_no_per_channel = chip_no_per_channel
        self.tsu = tsu
        
        # Initialize Chips
        self.chips = []
        for c in range(channel_count):
            channel_chips = []
            for i in range(chip_no_per_channel):
                chip_id = f"{id}.Chip_{c}_{i}"
                chip = FlashChip(chip_id, c, i, flash_technology, die_no, plane_no,
                                 read_latencies, program_latencies, erase_latency,
                                 suspend_program_latency, suspend_erase_latency)
                
                # Wire up signals: When chip is idle, tell TSU to service it
                chip.on_idle.connect(self.tsu.handle_chip_idle_signal)
                channel_chips.append(chip)
            self.chips.append(channel_chips)

    def get_chip(self, channel_id, chip_id):
        return self.chips[channel_id][chip_id]

    def execute_sim_event(self, event):
        pass
