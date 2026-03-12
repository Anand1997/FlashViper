import pytest
from mqsim.sim.engine import Engine
from mqsim.exec.execution_parameter_set import HostParameterSet, DeviceParameterSet
from mqsim.host.io_flow import SyntheticIOFlow
from mqsim.ssd.host_interface_nvme import HostInterfaceNVMe
from mqsim.ssd.ftl import FTL
from mqsim.ssd.nvm_phy import NVMPhy
from mqsim.nvm_chip.flash_chip import ChipStatus

def test_end_to_end_io_flow():
    engine = Engine()
    engine.reset()
    
    # 1. Setup SSD Components
    ftl = FTL(
        channel_no=1, chip_no_per_channel=1, die_no_per_chip=1, 
        plane_no_per_die=1, block_no_per_plane=10, page_no_per_block=4, 
        page_size_in_sectors=8, over_provisioning_ratio=0.07, seed=42
    )
    
    phy = NVMPhy(
        "Phy0", channel_count=1, chip_no_per_channel=1,
        flash_technology="SLC", die_no=1, plane_no=1,
        read_latencies=[1000], program_latencies=[5000], erase_latency=10000,
        tsu=ftl.tsu # This automates the signal wiring!
    )
    
    # 2. Setup Host Interface
    hi = HostInterfaceNVMe("HI0", 1000000, 1024, 1024, 8, 512, 16)
    stream_id = hi.create_new_stream("HIGH", 0, 500000, 0x1000, 0x2000)
    
    # 3. Setup Workload
    class Linker:
        def submit_io_request(self, req):
            user_req = hi.submit_io_request(stream_id, req)
            transactions = ftl.segment_user_request(user_req)
            ftl.tsu.prepare_for_transaction_submit()
            for tr in transactions:
                tr.address = {"channel": 0, "chip": 0, "die": 0, "plane": 0, "block": 0, "page": 0}
                ftl.tsu.submit_transaction(tr)
            ftl.tsu.schedule()
            
            # Initially, the chip is IDLE, so we must trigger the first service manually
            # Subsequent services happen via the on_idle signal
            ftl.tsu.service_chip_requests(phy.get_chip(0, 0))

    linker = Linker()
    # Generate 2 requests sequentially
    flow = SyntheticIOFlow("Flow0", 1.0, 0, 1000, 42, queue_depth=2, host_interface=linker)
    
    engine.add_object(flow)
    engine.add_object(phy.get_chip(0, 0))
    
    # 4. Start Simulation
    engine.start_simulation()
    
    # 5. Verify timing: t=1 (start) + 1000 (req1) + 1000 (req2) = 2001
    assert engine.time == 2001
    assert phy.get_chip(0, 0).status == ChipStatus.IDLE
