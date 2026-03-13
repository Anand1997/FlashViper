import pytest
from mqsim.ssd.ftl import FTL
from mqsim.ssd.user_request import UserRequest

def test_ftl_request_segmentation():
    # Setup FTL with 8 sectors per page
    ftl = FTL(
        id="TestFTL",
        channel_no=1, chip_no_per_channel=1, die_no_per_chip=1, 
        plane_no_per_die=1, block_no_per_plane=10, page_no_per_block=4, 
        page_size_in_sectors=8, over_provisioning_ratio=0.07, seed=42
    )
    
    # 1. Create a large read request (16 sectors = 2 pages)
    user_req = UserRequest(stream_id=0, type="READ", lsa=0, size_in_sectors=16)
    
    # 2. Segment the request
    transactions = ftl.segment_user_request(user_req)
    
    assert len(transactions) == 2
    assert transactions[0].lpa == 0
    assert transactions[1].lpa == 1
    
    # 3. Test LPA to PPA translation logic integration
    # Manually map LPA 0 to a PPA
    ftl.address_mapping_unit.update_mapping_info(stream_id=0, lpa=0, ppa=50)
    
    # Process transactions through translation (simulated)
    for tr in transactions:
        tr.ppa = ftl.address_mapping_unit.get_ppa(tr.stream_id, tr.lpa)
        
    assert transactions[0].ppa == 50
    assert transactions[1].ppa == -1 # Not mapped yet
