import pytest
from mqsim.sim.engine import Engine
from mqsim.ssd.tsu_outoforder import TSUOutOfOrder
from mqsim.nvm_chip.flash_chip import FlashChip, ChipStatus

class MockTransaction:
    def __init__(self, t_type, source, channel, chip):
        self.type = t_type
        self.source = source
        self.address = {"channel": channel, "chip": chip}
        self.related_read = None

def test_tsu_asynchronous_service():
    engine = Engine()
    engine.reset()
    
    tsu = TSUOutOfOrder(id="TSU0", channel_count=1, chip_no_per_channel=1)
    chip = FlashChip(
        "Chip0", 0, 0, "SLC", 1, 1, [1000], [5000], 10000
    )
    engine.add_object(chip)
    
    # Connect TSU to chip's on_idle signal
    chip.on_idle.connect(tsu.service_chip_requests)
    
    # 1. Create two transactions for the same chip
    tx1 = MockTransaction("READ", "USERIO", 0, 0)
    tx2 = MockTransaction("READ", "USERIO", 0, 0)
    
    tsu.prepare_for_transaction_submit()
    tsu.submit_transaction(tx1)
    tsu.submit_transaction(tx2)
    tsu.schedule() # Put them in queues
    
    # 2. Manually trigger the first service
    tsu.service_chip_requests(chip)
    
    assert chip.status == ChipStatus.BUSY
    assert len(tsu.user_read_queues[0][0]) == 1 # tx2 is still waiting
    
    # 3. Run simulation. When tx1 finishes, chip fires on_idle, 
    # TSU should catch it and automatically start tx2.
    engine.start_simulation()
    
    # Time should be 2000 (1000 for tx1 + 1000 for tx2)
    assert engine.time == 2000
    assert chip.status == ChipStatus.IDLE
    assert len(tsu.user_read_queues[0][0]) == 0 # Both finished
