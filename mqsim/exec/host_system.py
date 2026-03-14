class PCIeLink:
    def __init__(self, lane_count, lane_bandwidth_gb_per_sec):
        self.lane_count = lane_count
        self.lane_bandwidth = lane_bandwidth_gb_per_sec # in GB/s
        # Total bandwidth in bytes per nanosecond for easy calculation
        # (GB/s * 1e9) / 1e9 = GB/s = B/ns
        self.bandwidth_b_per_ns = (lane_count * lane_bandwidth_gb_per_sec)

    def get_transfer_delay(self, size_in_bytes):
        if self.bandwidth_b_per_ns <= 0:
            return 0
        return int(size_in_bytes / self.bandwidth_b_per_ns)

class PCIeRootComplex:
    def __init__(self, pcie_link, ssd_host_interface):
        self.pcie_link = pcie_link
        self.ssd_host_interface = ssd_host_interface

class PCIeSwitch:
    def __init__(self, pcie_link, ssd_host_interface):
        self.pcie_link = pcie_link
        self.ssd_host_interface = ssd_host_interface

class HostSystem:
    def __init__(self, parameters, preconditioning_required, ssd_host_interface):
        self.parameters = parameters
        self.preconditioning_required = preconditioning_required
        self.ssd_host_interface = ssd_host_interface
        
        # Initialize PCIe infrastructure
        self.pcie_link = PCIeLink(
            lane_count=parameters.pcie_lane_count,
            lane_bandwidth_gb_per_sec=parameters.pcie_lane_bandwidth
        )
        self.pcie_root_complex = PCIeRootComplex(self.pcie_link, ssd_host_interface)
        self.pcie_switch = PCIeSwitch(self.pcie_link, ssd_host_interface)
        
        # Link host interface back to PCIe link for delay calculations
        self.ssd_host_interface.pcie_link = self.pcie_link
        
        self.io_flows = []
        self.ssd_device = None

    def attach_ssd_device(self, ssd_device):
        self.ssd_device = ssd_device

    def add_io_flow(self, flow):
        self.io_flows.append(flow)

    def get_io_flows(self):
        return self.io_flows
