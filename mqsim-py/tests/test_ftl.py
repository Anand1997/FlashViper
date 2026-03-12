import pytest
from mqsim.ssd.ftl import FTL

def test_ftl_initialization():
    ftl = FTL(
        channel_no=8, 
        chip_no_per_channel=4, 
        die_no_per_chip=2, 
        plane_no_per_die=2, 
        block_no_per_plane=2048, 
        page_no_per_block=256, 
        page_size_in_sectors=16, 
        over_provisioning_ratio=0.07,
        seed=42
    )
    
    # Verify that the FTL successfully creates its sub-components
    assert ftl.block_manager is not None
    assert ftl.address_mapping_unit is not None
    assert ftl.tsu is not None
    
    # The number of logical pages is calculated based on physical capacity and OP ratio
    total_physical_pages = 8 * 4 * 2 * 2 * 2048 * 256
    expected_logical_pages = int(total_physical_pages * (1 - 0.07))
    assert ftl.address_mapping_unit.no_of_logical_pages == expected_logical_pages
