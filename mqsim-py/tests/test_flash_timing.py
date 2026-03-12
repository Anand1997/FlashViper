import pytest
from mqsim.sim.engine import Engine
from mqsim.nvm_chip.flash_chip import FlashChip, ChipStatus

def test_flash_chip_execution_event():
    engine = Engine()
    engine.reset()
    
    chip = FlashChip(
        obj_id="Chip0", channel_id=0, local_chip_id=0,
        flash_technology="SLC", die_no=1, planes_per_die=1,
        read_latencies=[1000], program_latencies=[5000], erase_latency=10000
    )
    engine.add_object(chip)
    
    # 1. Start a read command
    # Latency is 1000ns.
    chip.start_command_execution("READ_PAGE", page_id=0)
    
    assert chip.status == ChipStatus.BUSY
    
    # 2. Run simulation
    engine.start_simulation()
    
    # 3. Verify it finished at exactly t=1000
    assert engine.time == 1000
    assert chip.status == ChipStatus.IDLE
