from mqsim.sim.sim_object import SimObject
from mqsim.nvm_chip.flash_chip import FlashChip, DieStatus

class ChannelStatus:
    IDLE = 0
    BUSY = 1

class Channel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.status = ChannelStatus.IDLE

class NVMPhy(SimObject):
    def __init__(self, id, channel_count, chip_no_per_channel, 
                 flash_technology, die_no, plane_no,
                 read_latencies, program_latencies, erase_latency, tsu,
                 suspend_program_latency=0, suspend_erase_latency=0):
        super().__init__(id)
        self.channel_count = channel_count
        self.chip_no_per_channel = chip_no_per_channel
        self.tsu = tsu
        
        self.channels = [Channel(i) for i in range(channel_count)]
        
        # Initialize Chips
        self.chips = []
        for c in range(channel_count):
            channel_chips = []
            for i in range(chip_no_per_channel):
                chip_id = f"{id}.Chip_{c}_{i}"
                chip = FlashChip(chip_id, c, i, flash_technology, die_no, plane_no,
                                 read_latencies, program_latencies, erase_latency,
                                 suspend_program_latency, suspend_erase_latency)
                
                chip.on_idle.connect(self.tsu.handle_chip_idle_signal)
                channel_chips.append(chip)
            self.chips.append(channel_chips)

    def get_chip(self, channel_id, chip_id):
        return self.chips[channel_id][chip_id]

    def is_channel_busy(self, channel_id):
        return self.channels[channel_id].status == ChannelStatus.BUSY

    def start_transfer(self, channel_id, delay, callback_params):
        """
        Simulates a bus transfer (command, address, or data).
        """
        self.channels[channel_id].status = ChannelStatus.BUSY
        
        from mqsim.sim.engine import Engine
        Engine().register_sim_event(Engine().time + delay, self, 
                                     parameters={"type": "TRANSFER_DONE", "channel_id": channel_id, "payload": callback_params})

    def execute_sim_event(self, event):
        params = event.parameters
        if params["type"] == "TRANSFER_DONE":
            channel_id = params["channel_id"]
            self.channels[channel_id].status = ChannelStatus.IDLE
            
            payload = params["payload"]
            if payload["type"] == "START_CHIP_EXEC":
                chip = payload["chip"]
                chip.start_command_execution(payload["cmd_type"], payload["die_id"], payload["page_id"])
            
            # When bus is free, TSU might want to schedule another transfer
            # (Though MQSim usually waits for chip/die signals)
            # For simplicity, we trigger TSU to check all chips on this channel
            for chip in self.chips[channel_id]:
                for d_id in range(chip.die_no):
                    if chip.dies[d_id].status == DieStatus.IDLE:
                        self.tsu.service_chip_requests(chip, d_id)
