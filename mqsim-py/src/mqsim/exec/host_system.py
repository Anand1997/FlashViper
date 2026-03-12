class PCIeRootComplex:
    def __init__(self, pcie_link, ssd_host_interface):
        self.pcie_link = pcie_link
        self.ssd_host_interface = ssd_host_interface

class PCIeLink:
    def __init__(self, lane_count):
        self.lane_count = lane_count

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
        self.pcie_link = PCIeLink(lane_count=parameters.pcie_lane_count)
        self.pcie_root_complex = PCIeRootComplex(self.pcie_link, ssd_host_interface)
        self.pcie_switch = PCIeSwitch(self.pcie_link, ssd_host_interface)
        
        self.io_flows = []
        self.ssd_device = None

    def attach_ssd_device(self, ssd_device):
        self.ssd_device = ssd_device

    def add_io_flow(self, flow):
        self.io_flows.append(flow)

    def get_io_flows(self):
        return self.io_flows
