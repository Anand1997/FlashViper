import pytest
from mqsim.ssd.tsu_outoforder import TSUOutOfOrder
from mqsim.nvm_chip.flash_chip import ChipStatus

class MockTransaction:
    def __init__(self, t_type, source, channel, chip):
        self.type = t_type
        self.source = source
        self.address = {"channel": channel, "chip": chip, "page": 0}
        self.related_read = None
        self.user_request = None

class MockDie:
    def __init__(self):
        self.planes_per_die = 2
        self.status = ChipStatus.IDLE

class MockChip:
    def __init__(self, channel_id, chip_id):
        self.channel_id = channel_id
        self.chip_id = chip_id
        self.status = ChipStatus.IDLE
        self.dies = [MockDie()]

    def start_command_execution(self, command_type, die_id=0, page_id=0):
        pass

def test_tsu_outoforder_queuing():
    # Setup TSU: 2 channels, 2 chips per channel
    tsu = TSUOutOfOrder(id="TSU0", channel_count=2, chip_no_per_channel=2)
    
    # Create transactions
    tx1 = MockTransaction("READ", "USERIO", channel=0, chip=1)
    tx2 = MockTransaction("WRITE", "USERIO", channel=1, chip=0)
    
    tsu.prepare_for_transaction_submit()
    tsu.submit_transaction(tx1)
    tsu.submit_transaction(tx2)
    tsu.schedule()
    
    assert tx1 in tsu.user_read_queues[0][1]
    assert tx2 in tsu.user_write_queues[1][0]

def test_tsu_prioritization():
    tsu = TSUOutOfOrder(id="TSU0", channel_count=1, chip_no_per_channel=1)
    
    # Create a mix of transactions for the same chip
    user_read = MockTransaction("READ", "USERIO", 0, 0)
    gc_read = MockTransaction("READ", "GC_WL", 0, 0)
    mapping_read = MockTransaction("READ", "MAPPING", 0, 0)
    
    tsu.prepare_for_transaction_submit()
    tsu.submit_transaction(user_read)
    tsu.submit_transaction(gc_read)
    tsu.submit_transaction(mapping_read)
    tsu.schedule() # Distributes them to internal queues
    
    chip = MockChip(0, 0)
    
    # First service should pick MAPPING read
    serviced = tsu.service_read_transaction(chip, die_id=0)
    assert serviced is True
    assert len(tsu.mapping_read_queues[0][0]) == 0 # Popped
    
    # Second should pick GC read (assuming urgent mode is always true in our simple mock)
    serviced = tsu.service_read_transaction(chip, die_id=0)
    assert serviced is True
    assert len(tsu.gc_read_queues[0][0]) == 0
    
    # Third should pick USER read
    serviced = tsu.service_read_transaction(chip, die_id=0)
    assert serviced is True
    assert len(tsu.user_read_queues[0][0]) == 0
