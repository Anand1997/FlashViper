import pytest
from mqsim.exec.ssd_device import SSDDevice
from mqsim.exec.execution_parameter_set import DeviceParameterSet
from mqsim.ssd.ftl import FTL

def test_ssd_device_initialization():
    # Setup dummy device parameters
    params = DeviceParameterSet()
    params.memory_type = "FLASH"
    params.flash_channel_count = 4
    params.flash_params.flash_technology = "MLC"
    
    # Initialize the SSD Device
    ssd = SSDDevice(parameters=params, io_flows=[])
    
    # Verify core components are initialized
    assert ssd.memory_type == "FLASH"
    assert ssd.host_interface is not None
    assert ssd.cache_manager is not None
    assert ssd.firmware is not None
    
    # Verify that the FTL (Firmware) was given the correct config
    assert isinstance(ssd.firmware, FTL)
    assert ssd.firmware.channel_no == 4
    
    # Attach to a mock host switch
    class MockPCIeSwitch: pass
    switch = MockPCIeSwitch()
    
    ssd.attach_to_host(switch)
    assert ssd.host_interface.pcie_switch == switch
