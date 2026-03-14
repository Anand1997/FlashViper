import xml.etree.ElementTree as ET

class FlashParameterSet:
    def __init__(self):
        self.flash_technology = "SLC"
        self.page_read_latency_lsb = 0
        self.page_read_latency_csb = 0
        self.page_read_latency_msb = 0
        self.page_program_latency_lsb = 0
        self.page_program_latency_csb = 0
        self.page_program_latency_msb = 0
        self.die_no_per_chip = 2
        self.plane_no_per_die = 2
        self.block_no_per_plane = 2048
        self.page_no_per_block = 256
        self.page_capacity = 8192
        self.block_erase_latency = 3800000

    def deserialize(self, node):
        self.flash_technology = node.findtext("Flash_Technology")
        self.page_read_latency_lsb = int(node.findtext("Page_Read_Latency_LSB", "0"))
        self.page_read_latency_csb = int(node.findtext("Page_Read_Latency_CSB", "0"))
        self.page_read_latency_msb = int(node.findtext("Page_Read_Latency_MSB", "0"))
        self.page_program_latency_lsb = int(node.findtext("Page_Program_Latency_LSB", "0"))
        self.page_program_latency_csb = int(node.findtext("Page_Program_Latency_CSB", "0"))
        self.page_program_latency_msb = int(node.findtext("Page_Program_Latency_MSB", "0"))
        self.die_no_per_chip = int(node.findtext("Die_No_Per_Chip", "2"))
        self.plane_no_per_die = int(node.findtext("Plane_No_Per_Die", "2"))
        self.block_no_per_plane = int(node.findtext("Block_No_Per_Plane", "2048"))
        self.page_no_per_block = int(node.findtext("Page_No_Per_Block", "256"))
        self.page_capacity = int(node.findtext("Page_Capacity", "8192"))
        self.block_erase_latency = int(node.findtext("Block_Erase_Latency", "3800000"))

class DeviceParameterSet:
    def __init__(self):
        self.memory_type = "FLASH"
        self.flash_channel_count = 0
        self.chip_no_per_channel = 4
        self.flash_params = FlashParameterSet()
        self.seed = 321
        self.overprovisioning_ratio = 0.07
        self.data_cache_capacity = 268435456
        self.data_cache_dram_row_size = 8192
        self.data_cache_dram_data_rate = 100
        self.data_cache_dram_data_burst_size = 1
        self.data_cache_dram_tRCD = 13
        self.data_cache_dram_tCL = 13
        self.data_cache_dram_tRP = 13
        self.io_queue_depth = 65535
        self.queue_fetch_size = 512
        self.cmt_capacity = 1024 
        self.plane_allocation_scheme = "CWDP"
        self.data_cache_sharing_mode = "SHARED"
        self.ideal_mapping_table = False
        self.erase_suspension_enabled = False
        self.program_suspension_enabled = False

    def deserialize(self, node):
        self.memory_type = node.findtext("Memory_Type")
        self.flash_channel_count = int(node.findtext("Flash_Channel_Count", "0"))
        self.chip_no_per_channel = int(node.findtext("Chip_No_Per_Channel", "4"))
        self.seed = int(node.findtext("Seed", "321"))
        self.overprovisioning_ratio = float(node.findtext("Overprovisioning_Ratio", "0.07"))
        
        self.data_cache_capacity = int(node.findtext("Data_Cache_Capacity", "268435456"))
        self.data_cache_sharing_mode = node.findtext("Data_Cache_Sharing_Mode", "SHARED")
        self.ideal_mapping_table = node.findtext("Ideal_Mapping_Table", "false").lower() == "true"
        self.erase_suspension_enabled = node.findtext("Erase_Suspension_Enabled", "false").lower() == "true"
        self.program_suspension_enabled = node.findtext("Program_Suspension_Enabled", "false").lower() == "true"
        self.data_cache_dram_row_size = int(node.findtext("Data_Cache_DRAM_Row_Size", "8192"))
        self.data_cache_dram_data_rate = int(node.findtext("Data_Cache_DRAM_Data_Rate", "100"))
        # Note: XML has typo "Data_Cache_DRAM_Data_Busrt_Size"
        self.data_cache_dram_data_burst_size = int(node.findtext("Data_Cache_DRAM_Data_Busrt_Size", "1"))
        self.data_cache_dram_tRCD = int(node.findtext("Data_Cache_DRAM_tRCD", "13"))
        self.data_cache_dram_tCL = int(node.findtext("Data_Cache_DRAM_tCL", "13"))
        self.data_cache_dram_tRP = int(node.findtext("Data_Cache_DRAM_tRP", "13"))
        
        self.io_queue_depth = int(node.findtext("IO_Queue_Depth", "65535"))
        self.queue_fetch_size = int(node.findtext("Queue_Fetch_Size", "512"))
        self.cmt_capacity = int(node.findtext("CMT_Capacity", "1024"))
        self.plane_allocation_scheme = node.findtext("Plane_Allocation_Scheme", "CWDP")
        
        flash_node = node.find("Flash_Parameter_Set")
        if flash_node is not None:
            self.flash_params.deserialize(flash_node)

class HostParameterSet:
    def __init__(self):
        self.pcie_lane_count = 0
        self.pcie_lane_bandwidth = 1.0
        self.sata_processing_delay = 0
        self.io_flow_definitions = []

    def deserialize(self, node):
        self.pcie_lane_count = int(node.findtext("PCIe_Lane_Count", "4"))
        self.pcie_lane_bandwidth = float(node.findtext("PCIe_Lane_Bandwidth", "1.0"))
        self.sata_processing_delay = int(node.findtext("SATA_Processing_Delay", "0"))

class IOFlowParameterSet:
    def __init__(self):
        self.priority_class = "HIGH"
        self.device_level_data_caching_mode = "WRITE_CACHE"
        self.channel_ids = []
        self.chip_ids = []
        self.die_ids = []
        self.plane_ids = []
        self.initial_occupancy_percentage = 0

    def deserialize_base(self, node):
        self.priority_class = node.findtext("Priority_Class")
        self.device_level_data_caching_mode = node.findtext("Device_Level_Data_Caching_Mode")
        self.channel_ids = [int(x) for x in node.findtext("Channel_IDs").split(',')]
        self.chip_ids = [int(x) for x in node.findtext("Chip_IDs").split(',')]
        self.die_ids = [int(x) for x in node.findtext("Die_IDs").split(',')]
        self.plane_ids = [int(x) for x in node.findtext("Plane_IDs").split(',')]
        self.initial_occupancy_percentage = int(node.findtext("Initial_Occupancy_Percentage"))

class IOFlowParameterSetSynthetic(IOFlowParameterSet):
    def __init__(self):
        super().__init__()
        self.working_set_percentage = 85
        self.synthetic_generator_type = "QUEUE_DEPTH"
        self.read_percentage = 100
        self.address_distribution = "RANDOM_UNIFORM"
        self.percentage_of_hot_region = 0
        self.generated_aligned_addresses = True
        self.address_alignment_unit = 16
        self.request_size_distribution = "FIXED"
        self.average_request_size = 8
        self.variance_request_size = 0
        self.seed = 12344
        self.average_no_of_reqs_in_queue = 2
        self.stop_time = 1000000000
        self.total_requests_to_generate = 0

    def deserialize(self, node):
        self.deserialize_base(node)
        self.working_set_percentage = int(node.findtext("Working_Set_Percentage"))
        self.synthetic_generator_type = node.findtext("Synthetic_Generator_Type")
        self.read_percentage = int(node.findtext("Read_Percentage"))
        self.address_distribution = node.findtext("Address_Distribution")
        self.percentage_of_hot_region = int(node.findtext("Percentage_of_Hot_Region"))
        self.generated_aligned_addresses = node.findtext("Generated_Aligned_Addresses").lower() == "true"
        self.address_alignment_unit = int(node.findtext("Address_Alignment_Unit"))
        self.request_size_distribution = node.findtext("Request_Size_Distribution")
        self.average_request_size = int(node.findtext("Average_Request_Size"))
        self.variance_request_size = int(node.findtext("Variance_Request_Size"))
        self.seed = int(node.findtext("Seed"))
        self.average_no_of_reqs_in_queue = int(node.findtext("Average_No_of_Reqs_in_Queue"))
        self.stop_time = int(node.findtext("Stop_Time"))
        self.total_requests_to_generate = int(node.findtext("Total_Requests_To_Generate"))

class IOFlowParameterSetTraceBased(IOFlowParameterSet):
    def __init__(self):
        super().__init__()
        self.file_path = ""
        self.percentage_to_be_executed = 100
        self.relay_count = 1
        self.time_unit = "NANOSECOND"

    def deserialize(self, node):
        self.deserialize_base(node)
        self.file_path = node.findtext("File_Path")
        self.percentage_to_be_executed = int(node.findtext("Percentage_To_Be_Executed"))
        self.relay_count = int(node.findtext("Relay_Count"))
        self.time_unit = node.findtext("Time_Unit")

class IOScenario:
    def __init__(self):
        self.flow_definitions = []

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

    def deserialize_workload(self, file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        scenarios = []
        for scenario_node in root.findall("IO_Scenario"):
            scenario = IOScenario()
            for flow_node in scenario_node:
                if flow_node.tag == "IO_Flow_Parameter_Set_Synthetic":
                    flow = IOFlowParameterSetSynthetic()
                    flow.deserialize(flow_node)
                    scenario.flow_definitions.append(flow)
                elif flow_node.tag == "IO_Flow_Parameter_Set_Trace_Based":
                    flow = IOFlowParameterSetTraceBased()
                    flow.deserialize(flow_node)
                    scenario.flow_definitions.append(flow)
            scenarios.append(scenario)
        return scenarios
