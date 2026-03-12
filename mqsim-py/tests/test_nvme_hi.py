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

def test_nvme_submit_io_request():
    hi = HostInterfaceNVMe("HI0", 1000000, 1024, 1024, 8, 512, 16)
    stream_id = hi.create_new_stream("HIGH", 0, 500000, 0x1000, 0x2000)
    
    host_req = {
        'type': 'READ',
        'lsa': 100,
        'size': 8
    }
    
    user_req = hi.submit_io_request(stream_id, host_req)
    
    assert user_req.stream_id == stream_id
    assert user_req.type == 'READ'
    assert user_req.lsa == 100
    assert user_req.size_in_sectors == 8
    
    stream = hi.input_streams[stream_id]
    assert stream.on_the_fly_requests == 1
    assert len(stream.waiting_user_requests) == 1
    assert stream.submission_tail == 1
