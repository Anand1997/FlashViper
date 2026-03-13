import xml.etree.ElementTree as ET

class FlashParameterSet:
    def __init__(self):
        self.flash_technology = "SLC"
        self.page_read_latency_lsb = 0
        self.page_program_latency_lsb = 0
        self.die_no_per_chip = 2
        self.plane_no_per_die = 2
        self.block_no_per_plane = 2048
        self.page_no_per_block = 256
        self.page_capacity = 8192
        self.block_erase_latency = 3800000

    def deserialize(self, node):
        self.flash_technology = node.findtext("Flash_Technology")
        self.page_read_latency_lsb = int(node.findtext("Page_Read_Latency_LSB"))
        self.page_program_latency_lsb = int(node.findtext("Page_Program_Latency_LSB"))
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

    def deserialize(self, node):
        self.memory_type = node.findtext("Memory_Type")
        self.flash_channel_count = int(node.findtext("Flash_Channel_Count"))
        self.chip_no_per_channel = int(node.findtext("Chip_No_Per_Channel", "4"))
        self.seed = int(node.findtext("Seed", "321"))
        self.overprovisioning_ratio = float(node.findtext("Overprovisioning_Ratio", "0.07"))
        
        self.data_cache_capacity = int(node.findtext("Data_Cache_Capacity", "268435456"))
        self.data_cache_dram_row_size = int(node.findtext("Data_Cache_DRAM_Row_Size", "8192"))
        self.data_cache_dram_data_rate = int(node.findtext("Data_Cache_DRAM_Data_Rate", "100"))
        self.data_cache_dram_data_burst_size = int(node.findtext("Data_Cache_DRAM_Data_Busrt_Size", "1"))
        self.data_cache_dram_tRCD = int(node.findtext("Data_Cache_DRAM_tRCD", "13"))
        self.data_cache_dram_tCL = int(node.findtext("Data_Cache_DRAM_tCL", "13"))
        self.data_cache_dram_tRP = int(node.findtext("Data_Cache_DRAM_tRP", "13"))
        
        self.io_queue_depth = int(node.findtext("IO_Queue_Depth", "65535"))
        self.queue_fetch_size = int(node.findtext("Queue_Fetch_Size", "512"))
        
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
