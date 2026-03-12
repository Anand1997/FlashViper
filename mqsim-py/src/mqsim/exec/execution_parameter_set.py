import xml.etree.ElementTree as ET

class FlashParameterSet:
    def __init__(self):
        self.flash_technology = "SLC"
        self.page_read_latency_lsb = 0
        self.page_program_latency_lsb = 0

    def deserialize(self, node):
        self.flash_technology = node.findtext("Flash_Technology")
        self.page_read_latency_lsb = int(node.findtext("Page_Read_Latency_LSB"))
        self.page_program_latency_lsb = int(node.findtext("Page_Program_Latency_LSB"))

class DeviceParameterSet:
    def __init__(self):
        self.memory_type = "FLASH"
        self.flash_channel_count = 0
        self.flash_params = FlashParameterSet()

    def deserialize(self, node):
        self.memory_type = node.findtext("Memory_Type")
        self.flash_channel_count = int(node.findtext("Flash_Channel_Count"))
        
        flash_node = node.find("Flash_Parameter_Set")
        if flash_node is not None:
            self.flash_params.deserialize(flash_node)

class HostParameterSet:
    def __init__(self):
        self.pcie_lane_count = 0

    def deserialize(self, node):
        self.pcie_lane_count = int(node.findtext("PCIe_Lane_Count"))

class ExecutionParameterSet:
    def __init__(self):
        self.host_config = HostParameterSet()
        self.ssd_device_config = DeviceParameterSet()

    def deserialize(self, file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        host_node = root.find("Host_Parameter_Set")
        if host_node is not None:
            self.host_config.deserialize(host_node)
            
        device_node = root.find("Device_Parameter_Set")
        if device_node is not None:
            self.ssd_device_config.deserialize(device_node)
