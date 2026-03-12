import pytest
from mqsim.ssd.host_interface_nvme import HostInterfaceNVMe

def test_nvme_host_interface_stream_creation():
    # Setup Host Interface
    hi = HostInterfaceNVMe(
        id="HI0",
        max_lsa=1000000,
        submission_queue_depth=1024,
        completion_queue_depth=1024,
        no_of_input_streams=8,
        queue_fetch_size=512,
        sectors_per_page=16
    )
    
    # Create a new stream
    stream_id = hi.create_new_stream(
        priority_class="HIGH",
        start_lsa=0,
        end_lsa=500000,
        submission_queue_base_address=0x1000,
        completion_queue_base_address=0x2000
    )
    
    assert stream_id == 0
    assert len(hi.input_streams) == 1
    
    stream = hi.input_streams[0]
    assert stream.submission_queue_size == 1024
    assert stream.submission_queue_base_address == 0x1000
