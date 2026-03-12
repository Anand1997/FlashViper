import pytest
from mqsim.sim.engine import Engine
from mqsim.nvm_chip.flash_chip import FlashChip

def test_flash_chip_read_latency():
    engine = Engine()
    engine.reset()
    
    # Simple MLC flash chip setup
    read_latencies = [75000, 75000] # LSB, MSB
    prog_latencies = [750000, 750000]
    
    chip = FlashChip(
        obj_id="Chip0",
        channel_id=0,
        local_chip_id=0,
        flash_technology="MLC",
        die_no=2,
        planes_per_die=2,
        read_latencies=read_latencies,
        program_latencies=prog_latencies,
        erase_latency=3800000
    )
    
    # Test LSB page read latency (page 0 is LSB in MLC)
    latency = chip.get_command_execution_latency("READ_PAGE", 0)
    assert latency == 75000
    
    # Test LSB page program latency
    latency = chip.get_command_execution_latency("PROGRAM_PAGE", 0)
    assert latency == 750000
