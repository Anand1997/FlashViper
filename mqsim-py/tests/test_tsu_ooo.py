import pytest
from mqsim.ssd.tsu_outoforder import TSUOutOfOrder

class MockTransaction:
    def __init__(self, t_type, channel, chip):
        self.type = t_type
        self.address = {"channel": channel, "chip": chip}
        self.related_read = None

def test_tsu_outoforder_queuing():
    # Setup TSU: 2 channels, 2 chips per channel
    tsu = TSUOutOfOrder(id="TSU0", channel_count=2, chip_no_per_channel=2)
    
    # Create transactions
    tx1 = MockTransaction("READ", channel=0, chip=1)
    tx2 = MockTransaction("WRITE", channel=1, chip=0)
    
    # Submit and Schedule (Schedule performs the queuing in this simple port)
    tsu.prepare_for_transaction_submit()
    tsu.submit_transaction(tx1)
    tsu.submit_transaction(tx2)
    tsu.schedule()
    
    # Verify they are in the correct queues
    # tx1 -> UserReadTRQueue[0][1]
    assert tx1 in tsu.user_read_queues[0][1]
    
    # tx2 -> UserWriteTRQueue[1][0]
    assert tx2 in tsu.user_write_queues[1][0]
