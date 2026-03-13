import pytest
import subprocess
import os
import xml.etree.ElementTree as ET
import re

# Get the project root directory relative to this test file
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(TEST_DIR, "..", ".."))

def find_file(filename):
    # Search in common locations relative to project root or current directory
    search_paths = [
        os.path.join(PROJECT_ROOT, filename),
        os.path.join(os.getcwd(), filename),
        filename
    ]
    for path in search_paths:
        if os.path.exists(path):
            return os.path.abspath(path)
    return None

def run_cpp_sim(config_path, workload_path):
    # Run C++ simulation
    exe_path = find_file("MQSim.exe")
    if not exe_path:
        pytest.fail("MQSim.exe not found. Build it first.")
    
    config_abs = find_file(config_path)
    workload_abs = find_file(workload_path)
    
    if not config_abs or not workload_abs:
        pytest.fail(f"Config or Workload file not found: {config_path}, {workload_path}")

    cmd = [exe_path, "-i", config_abs, "-w", workload_abs]
    # Run in the project root to ensure output files are found where expected
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
    
    # MQSim C++ creates an output file named workload_filename_scenario_1.xml
    workload_name = os.path.splitext(os.path.basename(workload_path))[0]
    output_xml = os.path.join(PROJECT_ROOT, f"{workload_name}_scenario_1.xml")
    
    if not os.path.exists(output_xml):
        pytest.fail(f"C++ simulation did not produce {output_xml}")
        
    tree = ET.parse(output_xml)
    root = tree.getroot()
    
    # Extract metrics for the first flow
    flow = root.find(".//Host.IO_Flow")
    requests = int(flow.findtext("Request_Count"))
    latency = float(flow.findtext("Device_Response_Time"))
    
    return {"requests": requests, "latency": latency}

def run_python_sim(config_path, workload_path):
    # Run Python simulation
    main_py = os.path.join(PROJECT_ROOT, "mqsim-py", "src", "mqsim", "main.py")
    if not os.path.exists(main_py):
        pytest.fail(f"main.py not found at {main_py}")

    config_abs = find_file(config_path)
    workload_abs = find_file(workload_path)
    
    env = os.environ.copy()
    # Add mqsim-py/src to PYTHONPATH
    src_dir = os.path.join(PROJECT_ROOT, "mqsim-py", "src")
    env["PYTHONPATH"] = src_dir
    
    cmd = ["python", main_py, "-i", config_abs, "-w", workload_abs]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=PROJECT_ROOT)
    
    if result.returncode != 0:
        pytest.fail(f"Python simulation failed with error:\n{result.stderr}")
        
    # Parse metrics from stdout using regex
    # Example: Flow Host.IO_Flow.Synth.No_0 - total requests generated: 50 total requests serviced: 50
    #          - device response time: 40 (us)
    
    stdout = result.stdout
    req_match = re.search(r"total requests serviced: (\d+)", stdout)
    lat_match = re.search(r"device response time: (\d+) \(us\)", stdout)
    
    if not req_match or not lat_match:
        pytest.fail(f"Could not parse Python simulation results from stdout:\n{stdout}")
        
    requests = int(req_match.group(1))
    latency = float(lat_match.group(1))
    
    return {"requests": requests, "latency": latency}

@pytest.mark.parametrize("config, workload", [
    ("ssdconfig.xml", "workload_small.xml"),
])
def test_simulation_parity(config, workload):
    print(f"\nRunning parity test for {workload}...")
    
    cpp_results = run_cpp_sim(config, workload)
    py_results = run_python_sim(config, workload)
    
    print(f"C++ Results: {cpp_results}")
    print(f"Python Results: {py_results}")
    
    # Assert Parity
    assert py_results["requests"] == cpp_results["requests"], "Request count mismatch!"
    
    # Latency should be close (within 10% or absolute 2us)
    assert abs(py_results["latency"] - cpp_results["latency"]) <= max(2, 0.1 * cpp_results["latency"]), \
        f"Latency mismatch! CP={cpp_results['latency']}us, PY={py_results['latency']}us"
