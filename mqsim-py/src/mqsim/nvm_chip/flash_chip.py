from mqsim.sim.sim_object import SimObject
from mqsim.sim.engine import Engine
from mqsim.utils.signal import Signal

class ChipStatus:
    IDLE = 0
    BUSY = 1

class DieStatus:
    IDLE = 0
    BUSY = 1

class Die:
    def __init__(self, die_id, planes_per_die):
        self.die_id = die_id
        self.planes_per_die = planes_per_die
        self.status = DieStatus.IDLE
        self.current_command = None
        self.on_idle = Signal()

class FlashChip(SimObject):
    def __init__(self, obj_id, channel_id, local_chip_id, 
                 flash_technology, die_no, planes_per_die,
                 read_latencies, program_latencies, erase_latency):
        super().__init__(obj_id)
        self.channel_id = channel_id
        self.chip_id = local_chip_id
        self.flash_technology = flash_technology
        self.die_no = die_no
        self.planes_per_die = planes_per_die
        self.read_latencies = read_latencies
        self.program_latencies = program_latencies
        self.erase_latency = erase_latency
        
        self.dies = [Die(i, planes_per_die) for i in range(die_no)]
        
        # We can still track an overall chip status if needed, but execution is per-die
        self.on_idle = Signal()

    @property
    def status(self):
        # A chip is considered completely IDLE only if ALL dies are IDLE
        # However, for issuing commands, we check the specific Die's status.
        return ChipStatus.BUSY if any(d.status == DieStatus.BUSY for d in self.dies) else ChipStatus.IDLE

    def get_command_execution_latency(self, command_type, page_id):
        latency_type = 0
        if self.flash_technology == "MLC":
            latency_type = page_id % 2
        elif self.flash_technology == "TLC":
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

    def start_command_execution(self, command_type, die_id, page_id):
        die = self.dies[die_id]
        if die.status != DieStatus.IDLE:
            raise RuntimeError(f"Cannot start command on busy die {die_id} of chip {self.id}")
            
        die.status = DieStatus.BUSY
        latency = self.get_command_execution_latency(command_type, page_id)
        
        # Schedule completion event
        engine = Engine()
        engine.register_sim_event(engine.time + latency, self, parameters={"die_id": die_id, "command_type": command_type})

    def execute_sim_event(self, event):
        params = event.parameters
        die_id = params["die_id"]
        die = self.dies[die_id]
        
        # Command finished on this die
        die.status = DieStatus.IDLE
        die.current_command = None
        
        # Notify listeners (e.g. TSU) that THIS die is now idle
        # We pass the die_id so the TSU knows which die is free
        self.on_idle.fire(self, die_id)
