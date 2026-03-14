import pytest
from mqsim.ssd.mapping_unit import PageLevelAddressMapping

def test_page_level_mapping_basic():
    # Setup mapping for 1000 logical pages
    mapping = PageLevelAddressMapping(no_of_logical_pages=1000)
    
    # Initial PPA should be invalid/none (using -1 or custom value)
    assert mapping.get_ppa(stream_id=0, lpa=10) == -1
    
    # Update mapping: LPA 10 maps to PPA 500
    mapping.update_mapping_info(stream_id=0, lpa=10, ppa=500)
    
    assert mapping.get_ppa(stream_id=0, lpa=10) == 500
    assert mapping.get_ppa(stream_id=0, lpa=11) == -1
