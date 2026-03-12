import pytest
import os
from mqsim.exec.execution_parameter_set import ExecutionParameterSet

def test_parse_ssd_config():
    # Path to original ssdconfig.xml
    config_path = "ssdconfig.xml"
    if not os.path.exists(config_path):
        # Fallback if running from different root
        config_path = "../ssdconfig.xml"
    
    params = ExecutionParameterSet()
    params.deserialize(config_path)
    
    # Check some known values from ssdconfig.xml
    assert params.host_config.pcie_lane_count == 4
    assert params.ssd_device_config.memory_type == "FLASH"
    assert params.ssd_device_config.flash_channel_count == 8
    assert params.ssd_device_config.flash_params.flash_technology == "MLC"
