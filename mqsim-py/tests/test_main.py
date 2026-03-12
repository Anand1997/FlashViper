import pytest
import os
from mqsim.exec.execution_parameter_set import ExecutionParameterSet
from mqsim.exec.host_system import HostSystem
from mqsim.exec.ssd_device import SSDDevice

def test_main_orchestration():
    # 1. Parse configuration
    config_path = "../ssdconfig.xml"
    if not os.path.exists(config_path):
        config_path = "ssdconfig.xml"
        
    params = ExecutionParameterSet()
    params.deserialize(config_path)
    
    # 2. Instantiate Host System
    # Note: We pass None for ssd_host_interface for now to break circular init dependency
    host = HostSystem(
        parameters=params.host_config,
        preconditioning_required=False,
        ssd_host_interface=None
    )
    
    # 3. Instantiate SSD Device
    ssd = SSDDevice(
        parameters=params.ssd_device_config,
        io_flows=[]
    )
    
    # 4. Wire them together (Attachment)
    host.attach_ssd_device(ssd)
    ssd.attach_to_host(host.pcie_switch)
    
    # Verify the wiring is correct
    assert host.ssd_device == ssd
    assert ssd.host_interface.pcie_switch == host.pcie_switch
