import pytest
from mqsim.exec.host_system import HostSystem
from mqsim.exec.execution_parameter_set import HostParameterSet
from mqsim.host.io_flow import SyntheticIOFlow

class MockSSDInterface:
    pass

class MockSSDDevice:
    pass

def test_host_system_initialization():
    # Setup dummy parameters
    params = HostParameterSet()
    params.pcie_lane_count = 4
    
    ssd_interface = MockSSDInterface()
    
    host = HostSystem(params, preconditioning_required=False, ssd_host_interface=ssd_interface)
    
    # Verify PCIe components are instantiated
    assert host.pcie_root_complex is not None
    assert host.pcie_link is not None
    assert host.pcie_switch is not None
    
    # Verify that we can attach an SSD and add flows
    ssd_device = MockSSDDevice()
    host.attach_ssd_device(ssd_device)
    assert host.ssd_device == ssd_device
    
    flow = SyntheticIOFlow(0.5, 0, 1000, 42)
    host.add_io_flow(flow)
    assert len(host.get_io_flows()) == 1
    assert host.get_io_flows()[0] == flow
