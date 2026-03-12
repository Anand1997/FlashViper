import pytest
from mqsim.ssd.gc_and_wl_unit import GCUnit
from mqsim.ssd.flash_block_manager import FlashBlockManager

def test_gc_victim_selection_greedy():
    # Setup FBM
    fbm = FlashBlockManager(1, 1, 1, 1, 10, 4)
    plane_addr = {"channel": 0, "chip": 0, "die": 0, "plane": 0}
    
    # Simulate blocks being in use (remove from free pool)
    plane_record = fbm._get_plane_bookkeeping(plane_addr)
    plane_record.free_block_pool.remove(0)
    plane_record.free_block_pool.remove(1)
    plane_record.free_block_pool.remove(2)

    # Manually invalidate pages in some blocks
    # Block 0: 1 invalid page
    fbm.invalidate_page(plane_addr, 0, 0)
    
    # Block 1: 3 invalid pages (Victim!)
    fbm.invalidate_page(plane_addr, 1, 0)
    fbm.invalidate_page(plane_addr, 1, 1)
    fbm.invalidate_page(plane_addr, 1, 2)
    
    # Block 2: 2 invalid pages
    fbm.invalidate_page(plane_addr, 2, 0)
    fbm.invalidate_page(plane_addr, 2, 1)
    
    # Setup GC Unit
    gc = GCUnit(id="GC0", block_manager=fbm, block_selection_policy="GREEDY")
    
    # Select victim
    victim_block_id = gc.select_victim_block(plane_addr)
    
    assert victim_block_id == 1
