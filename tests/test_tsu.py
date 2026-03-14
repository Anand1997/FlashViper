import pytest
from mqsim.ssd.tsu_base import TSUBase

class MockTransaction:
    def __init__(self, t_type):
        self.type = t_type
        # RelatedRead mock (if None, ready to execute)
        self.related_read = None 

class MockTSU(TSUBase):
    def __init__(self):
        super().__init__()
        self.scheduled_transactions = []
        
    def schedule(self):
        # A very simplified scheduler: just accept everything ready
        for trans in self.transaction_receive_slots:
            if self._transaction_is_ready(trans):
                self.scheduled_transactions.append(trans)
        self.transaction_receive_slots.clear()
        
    def service_read_transaction(self, chip): pass
    def service_write_transaction(self, chip): pass
    def service_erase_transaction(self, chip): pass

def test_tsu_batch_submission():
    tsu = MockTSU()
    
    # 1. Start batch
    tsu.prepare_for_transaction_submit()
    
    # 2. Add transactions
    read_tx = MockTransaction("READ")
    write_tx = MockTransaction("WRITE")
    
    # Simulate a write waiting on a read (e.g. Copyback or GC)
    waiting_write_tx = MockTransaction("WRITE")
    waiting_write_tx.related_read = read_tx
    
    tsu.submit_transaction(read_tx)
    tsu.submit_transaction(write_tx)
    tsu.submit_transaction(waiting_write_tx)
    
    # 3. Schedule
    tsu.schedule()
    
    # Only the first two should be ready and scheduled
    assert len(tsu.scheduled_transactions) == 2
    assert tsu.scheduled_transactions[0] == read_tx
    assert tsu.scheduled_transactions[1] == write_tx
