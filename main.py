import sys
import os
import argparse
import time
from mqsim.sim.engine import Engine
from mqsim.exec.execution_parameter_set import ExecutionParameterSet
from mqsim.exec.host_system import HostSystem
from mqsim.exec.ssd_device import SSDDevice
from mqsim.host.io_flow import SyntheticIOFlow

def main():
    parser = argparse.ArgumentParser(description='MQSim Python Simulator')
    parser.add_argument('-i', '--input', required=True, help='Path to SSD configuration file')
    parser.add_argument('-w', '--workload', required=True, help='Path to workload definition file')
    
    args = parser.parse_args()
    
    ssd_config_path = args.input
    workload_path = args.workload
    
    if not os.path.exists(ssd_config_path):
        print(f"Error: SSD configuration file {ssd_config_path} not found.")
        return 1
        
    if not os.path.exists(workload_path):
        print(f"Error: Workload definition file {workload_path} not found.")
        return 1

    # 1. Parse configuration
    exec_params = ExecutionParameterSet()
    exec_params.deserialize(ssd_config_path)
    scenarios = exec_params.deserialize_workload(workload_path)
    
    engine = Engine()
    
    for i, scenario in enumerate(scenarios):
        start_time_wall = time.time()
        print(f"******************************")
        print(f"Executing scenario {i+1} out of {len(scenarios)} .......")
        
        # Reset the engine for each scenario
        engine.reset()
        
        # 2. Instantiate SSD Device
        ssd = SSDDevice(
            parameters=exec_params.ssd_device_config,
            host_parameters=exec_params.host_config,
            io_flows=scenario.flow_definitions
        )
        
        # 3. Instantiate Host System
        host = HostSystem(
            parameters=exec_params.host_config,
            preconditioning_required=False, # We check it below
            ssd_host_interface=ssd.host_interface
        )
        host.attach_ssd_device(ssd)
        ssd.attach_to_host(host.pcie_switch)
        
        # Preconditioning - Temporarily disabled for speed comparison
        # ssd.perform_preconditioning(scenario.flow_definitions)
        
        # 4. Create IO Flows based on scenario definitions
        for j, flow_def in enumerate(scenario.flow_definitions):
            stream_id = ssd.host_interface.create_new_stream(
                priority_class=flow_def.priority_class,
                start_lsa=0, 
                end_lsa=ssd.host_interface.max_lsa,
                submission_queue_base_address=0x1000 * j,
                completion_queue_base_address=0x2000 * j
            )
            
            if hasattr(flow_def, 'read_percentage'):
                read_ratio = flow_def.read_percentage / 100.0
                
                # Apply working set percentage
                end_lsa = int(ssd.host_interface.max_lsa * (flow_def.working_set_percentage / 100.0))
                
                # Cap stop time at 10ms (10,000,000 ns) for comparison
                capped_stop_time = min(flow_def.stop_time, 10000000)

                flow = SyntheticIOFlow(
                    id=f"Host.IO_Flow.Synth.No_{j}",
                    stream_id=stream_id,
                    read_ratio=read_ratio,
                    start_lsa=0,
                    end_lsa=end_lsa,
                    seed=flow_def.seed,
                    queue_depth=flow_def.average_no_of_reqs_in_queue,
                    stop_time=capped_stop_time,
                    total_req_count=flow_def.total_requests_to_generate,
                    host_interface=ssd.host_interface
                )
                host.add_io_flow(flow)
                engine.add_object(flow)
                # Link HI back to flow for completion notification
                ssd.host_interface.set_io_flow(stream_id, flow)
        
        # Add SSD components to engine
        engine.add_object(ssd.host_interface)
        # engine.add_object(ssd.cache_manager)
        # engine.add_object(ssd.firmware)
        # engine.add_object(ssd.phy)
        for channel in ssd.phy.chips:
            for chip in channel:
                engine.add_object(chip)
        
        # 5. Start Simulation
        print("Simulation started ...")
        engine.start_simulation()
        
        end_time_wall = time.time()
        duration = end_time_wall - start_time_wall
        print(f"Scenario {i+1} finished. Wall-clock time: {duration:.2f} seconds")
        
        # 6. Report Results in XML
        from mqsim.utils.xml_writer import XmlWriter
        xml_writer = XmlWriter()
        xml_writer.write_open_tag("MQSim_Results")
        
        host.report_results_in_xml("", xml_writer)
        ssd.report_results_in_xml("", xml_writer)
        
        xml_writer.write_close_tag()
        
        # Generate output filename: <workload_base>_scenario_<id>.xml
        workload_base = os.path.splitext(os.path.basename(workload_path))[0]
        output_filename = f"{workload_base}_scenario_{i+1}.xml"
        output_path = os.path.join(os.path.dirname(workload_path), output_filename)
        
        print(f"Writing results to output file {output_filename} .......")
        xml_writer.save_to_file(output_path)

        # 7. Basic Results Comparison (Console)
        for flow in host.get_io_flows():
            avg_lat = 0
            if flow.serviced_request_count > 0:
                avg_lat = flow.total_device_response_time / flow.serviced_request_count
            print(f"Flow {flow.id} - total requests generated: {flow.generated_request_count} total requests serviced: {flow.serviced_request_count}")
            print(f"                   - device response time: {avg_lat/1000:.0f} (us)")

    print("All scenarios complete.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
