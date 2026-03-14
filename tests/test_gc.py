import pytest
from mqsim.ssd.gc_and_wl_unit import GCUnit
from mqsim.ssd.flash_block_manager import FlashBlockManager

class MockTSU:
    def __init__(self):
        self.submitted_transactions = []
        
    def prepare_for_transaction_submit(self):
        pass
        
    def submit_transaction(self, tx):
        self.submitted_transactions.append(tx)
        
    def schedule(self):
        pass

def test_gc_victim_selection_greedy():
    # Setup FBM
    fbm = FlashBlockManager(1, 1, 1, 1, 10, 4)
    plane_addr = {"channel": 0, "chip": 0, "die": 0, "plane": 0}
    
    # Simulate blocks being in use (remove from free pool)
    plane_record = fbm._get_plane_bookkeeping(plane_addr)
    plane_record.free_block_pool.remove(0)
    plane_record.free_block_pool.remove(1)
    plane_record.free_block_pool.remove(2)

    # Set write index to simulate written pages
    plane_record.blocks[0].current_page_write_index = 4
    plane_record.blocks[1].current_page_write_index = 4
    plane_record.blocks[2].current_page_write_index = 4

    # Manually invalidate pages in some blocks
    # Block 0: 1 invalid page
    fbm.invalidate_page(plane_addr, 0, 0)
    
    # Block 1: 3 invalid pages (Victim!) -> 1 valid page remains (page 3)
    fbm.invalidate_page(plane_addr, 1, 0)
    fbm.invalidate_page(plane_addr, 1, 1)
    fbm.invalidate_page(plane_addr, 1, 2)
    
    # Block 2: 2 invalid pages
    fbm.invalidate_page(plane_addr, 2, 0)
    fbm.invalidate_page(plane_addr, 2, 1)
    
    tsu = MockTSU()
    # Setup GC Unit
    gc = GCUnit(id="GC0", block_manager=fbm, tsu=tsu, block_selection_policy="GREEDY")
    
    # Check GC required and perform GC
    victim_block_id = gc.check_gc_required(plane_addr)
    
    assert victim_block_id == 1
    
    # We expect 1 READ transaction (for the 1 valid page) and 1 ERASE transaction
    assert len(tsu.submitted_transactions) == 2
    
    reads = [t for t in tsu.submitted_transactions if t.type == "READ"]
    erases = [t for t in tsu.submitted_transactions if t.type == "ERASE"]
    
    assert len(reads) == 1
    assert len(erases) == 1
    
    # The read transaction should be for block 1, page 3 (the only valid page)
    assert reads[0].address["block"] == 1
    assert reads[0].address["page"] == 3
    assert erases[0].address["block"] == 1
