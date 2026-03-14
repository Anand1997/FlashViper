import pytest
import os
from mqsim.exec.execution_parameter_set import ExecutionParameterSet

# Get the project root directory relative to this test file
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TEST_DIR, "..", ".."))

def test_parse_ssd_config():
    # Path to original ssdconfig.xml
    config_path = os.path.join(PROJECT_ROOT, "ssdconfig.xml")
    if not os.path.exists(config_path):
        pytest.fail(f"ssdconfig.xml not found at {config_path}")
    
    params = ExecutionParameterSet()
    params.deserialize(config_path)
    
    # Check some known values from ssdconfig.xml
    assert params.host_config.pcie_lane_count == 4
    assert params.ssd_device_config.memory_type == "FLASH"
    assert params.ssd_device_config.flash_channel_count == 8
    assert params.ssd_device_config.flash_params.flash_technology == "MLC"
