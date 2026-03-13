import pytest
import os
from mqsim.exec.execution_parameter_set import ExecutionParameterSet

# Get the project root directory relative to this test file
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TEST_DIR, "..", ".."))

def test_workload_deserialization():
    config_path = os.path.join(PROJECT_ROOT, "workload.xml")
    if not os.path.exists(config_path):
        pytest.fail(f"workload.xml not found at {config_path}")
        
    exec_params = ExecutionParameterSet()
    scenarios = exec_params.deserialize_workload(config_path)
    
    # workload.xml has 3 scenarios
    assert len(scenarios) == 3
    
    # Scenario 0 has 2 synthetic flows
    assert len(scenarios[0].flow_definitions) == 2
    assert scenarios[0].flow_definitions[0].priority_class == "HIGH"
    assert scenarios[0].flow_definitions[0].channel_ids == [0,1,2,3,4,5,6,7]
    
    # Scenario 2 has 1 trace-based flow
    assert len(scenarios[2].flow_definitions) == 1
    assert scenarios[2].flow_definitions[0].file_path == "traces/tpcc-small.trace"
    assert scenarios[2].flow_definitions[0].time_unit == "NANOSECOND"
