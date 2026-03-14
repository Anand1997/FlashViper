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
        self.suspended_command = None
        self.remaining_exec_time = 0
        self.expected_finish_time = 0
        self.finish_event = None
        self.on_idle = Signal()

class FlashChip(SimObject):
    def __init__(self, obj_id, channel_id, local_chip_id, 
                 flash_technology, die_no, planes_per_die,
                 read_latencies, program_latencies, erase_latency,
                 suspend_program_latency=0, suspend_erase_latency=0):
        super().__init__(obj_id)
        self.channel_id = channel_id
        self.chip_id = local_chip_id
        self.flash_technology = flash_technology
        self.die_no = die_no
        self.planes_per_die = planes_per_die
        self.read_latencies = read_latencies
        self.program_latencies = program_latencies
        self.erase_latency = erase_latency
        self.suspend_program_latency = suspend_program_latency
        self.suspend_erase_latency = suspend_erase_latency
        
        self.dies = [Die(i, planes_per_die) for i in range(die_no)]
        self.on_idle = Signal()

    @property
    def status(self):
        return ChipStatus.BUSY if any(d.status == DieStatus.BUSY for d in self.dies) else ChipStatus.IDLE

    def get_command_execution_latency(self, command_type, page_id):
        latency_type = 0
        if self.flash_technology == "MLC":
            latency_type = page_id % 2
        elif self.flash_technology == "TLC":
            # From MQSim reference:
            # (pageID <= 5) ? 0 : ((pageID <= 7) ? 1 : (((pageID - 8) >> 1) % 3))
            if page_id <= 5:
                latency_type = 0
            elif page_id <= 7:
                latency_type = 1
            else:
                latency_type = ((page_id - 8) >> 1) % 3
        else: # SLC
            latency_type = 0

        # Safety: ensure latency_type doesn't exceed available slots
        latency_type = min(latency_type, len(self.read_latencies) - 1)

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
        
        die.expected_finish_time = Engine().time + latency
        die.current_command = command_type
        die.finish_event = Engine().register_sim_event(die.expected_finish_time, self, 
                                                       parameters={"die_id": die_id, "command_type": command_type})

    def suspend(self, die_id):
        die = self.dies[die_id]
        if die.status != DieStatus.BUSY:
            return
            
        die.remaining_exec_time = die.expected_finish_time - Engine().time
        Engine().ignore_sim_event(die.finish_event)
        die.finish_event = None
        
        die.suspended_command = die.current_command
        die.current_command = None
        die.status = DieStatus.IDLE
        # Notify TSU that this die is now free to take another command (e.g. READ)
        self.on_idle.fire(self, die_id)

    def resume(self, die_id):
        die = self.dies[die_id]
        if die.suspended_command is None:
            return
            
        die.status = DieStatus.BUSY
        die.current_command = die.suspended_command
        die.suspended_command = None
        
        die.expected_finish_time = Engine().time + die.remaining_exec_time
        die.finish_event = Engine().register_sim_event(die.expected_finish_time, self,
                                                       parameters={"die_id": die_id, "command_type": die.current_command})

    def execute_sim_event(self, event):
        params = event.parameters
        die_id = params["die_id"]
        die = self.dies[die_id]
        
        die.status = DieStatus.IDLE
        die.current_command = None
        die.finish_event = None
        
        self.on_idle.fire(self, die_id)
