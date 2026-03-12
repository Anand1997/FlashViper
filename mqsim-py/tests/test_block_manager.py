import pytest
from mqsim.ssd.flash_block_manager import FlashBlockManager

def test_flash_block_manager():
    # Setup a simple block manager: 1 channel, 1 chip, 1 die, 1 plane, 10 blocks per plane, 4 pages per block
    fbm = FlashBlockManager(
        channel_count=1,
        chip_no_per_channel=1,
        die_no_per_chip=1,
        plane_no_per_die=1,
        block_no_per_plane=10,
        page_no_per_block=4
    )
    
    # Define a target plane address
    plane_addr = {"channel": 0, "chip": 0, "die": 0, "plane": 0}
    
    # Allocate a page for user write
    address = fbm.allocate_page_for_user_write(0, plane_addr)
    
    # Check that we got the first block (0) and first page (0)
    assert address["block"] == 0
    assert address["page"] == 0
    
    # Allocate three more pages to fill the first block
    for i in range(1, 4):
        addr = fbm.allocate_page_for_user_write(0, plane_addr)
        assert addr["block"] == 0
        assert addr["page"] == i
        
    # The next allocation should move to the next block
    next_addr = fbm.allocate_page_for_user_write(0, plane_addr)
    assert next_addr["block"] == 1
    assert next_addr["page"] == 0
    
    # Test invalidation
    # Invalidate block 0, page 0
    fbm.invalidate_page(plane_addr, block_id=0, page_id=0)
    invalid_count = fbm.get_invalid_page_count(plane_addr, block_id=0)
    assert invalid_count == 1
