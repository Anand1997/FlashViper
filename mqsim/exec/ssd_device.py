from mqsim.ssd.ftl import FTL
from mqsim.ssd.data_cache_manager import DataCacheManagerSimple, CachingMode
from mqsim.ssd.host_interface_nvme import HostInterfaceNVMe
from mqsim.ssd.nvm_phy import NVMPhy

class SSDDevice:
    def __init__(self, parameters, io_flows):
        self.parameters = parameters
        self.io_flows = io_flows
        self.memory_type = parameters.memory_type
        self.channel_count = parameters.flash_channel_count
        self.chip_no_per_channel = getattr(parameters, 'chip_no_per_channel', 4)
        
        # 1. Host Interface
        self.host_interface = HostInterfaceNVMe(
            id="SSDDevice.HostInterface",
            max_lsa=1024*1024*1024, 
            submission_queue_depth=parameters.io_queue_depth,
            completion_queue_depth=parameters.io_queue_depth,
            no_of_input_streams=len(io_flows) if io_flows else 1,
            queue_fetch_size=parameters.queue_fetch_size,
            sectors_per_page=parameters.flash_params.page_capacity // 512
        )
        
        # 2. NVM Firmware (FTL)
        self.firmware = FTL(
            id="SSDDevice.FTL",
            channel_no=self.channel_count,
            chip_no_per_channel=self.chip_no_per_channel,
            die_no_per_chip=parameters.flash_params.die_no_per_chip,
            plane_no_per_die=parameters.flash_params.plane_no_per_die,
            block_no_per_plane=parameters.flash_params.block_no_per_plane,
            page_no_per_block=parameters.flash_params.page_no_per_block,
            page_size_in_sectors=parameters.flash_params.page_capacity // 512,
            over_provisioning_ratio=parameters.overprovisioning_ratio,
            seed=parameters.seed,
            cmt_capacity=parameters.cmt_capacity,
            stream_count=len(io_flows) if io_flows else 1
        )
        self.firmware.set_host_interface(self.host_interface)
        
        # Calculate max LSA based on logical pages
        self.host_interface.max_lsa = self.firmware.address_mapping_unit.no_of_logical_pages * self.firmware.page_size_in_sectors - 1
        read_latencies = [parameters.flash_params.page_read_latency_lsb, parameters.flash_params.page_read_latency_lsb]
        program_latencies = [parameters.flash_params.page_program_latency_lsb, parameters.flash_params.page_program_latency_lsb]
        
        self.phy = NVMPhy(
            id="SSDDevice.PHY",
            channel_count=self.channel_count,
            chip_no_per_channel=self.chip_no_per_channel,
            flash_technology=parameters.flash_params.flash_technology,
            die_no=parameters.flash_params.die_no_per_chip,
            plane_no=parameters.flash_params.plane_no_per_die,
            read_latencies=read_latencies,
            program_latencies=program_latencies,
            erase_latency=parameters.flash_params.block_erase_latency,
            tsu=self.firmware.tsu,
            suspend_program_latency=getattr(parameters.flash_params, 'suspend_program_latency', 0),
            suspend_erase_latency=getattr(parameters.flash_params, 'suspend_erase_latency', 0)
        )
        self.firmware.phy = self.phy
        self.firmware.tsu.phy = self.phy
        self.firmware.gc_and_wl_unit.phy = self.phy

        # 4. Data Cache Manager
        caching_modes = [CachingMode.WRITE_CACHE] * len(io_flows) if io_flows else [CachingMode.WRITE_CACHE]
        
        self.cache_manager = DataCacheManagerSimple(
            id="SSDDevice.CacheManager",
            host_interface=self.host_interface,
            nvm_firmware=self.firmware,
            total_capacity_in_bytes=parameters.data_cache_capacity,
            page_capacity_in_bytes=parameters.flash_params.page_capacity,
            dram_row_size=parameters.data_cache_dram_row_size,
            dram_data_rate=parameters.data_cache_dram_data_rate,
            dram_burst_size=parameters.data_cache_dram_data_burst_size,
            dram_tRCD=parameters.data_cache_dram_tRCD,
            dram_tCL=parameters.data_cache_dram_tCL,
            dram_tRP=parameters.data_cache_dram_tRP,
            caching_mode_per_input_stream=caching_modes,
            stream_count=len(caching_modes)
        )
        
        self.host_interface.cache_manager = self.cache_manager
        self.firmware.data_cache_manager = self.cache_manager
        
        self.channels = [] 

    def attach_to_host(self, pcie_switch):
        self.host_interface.pcie_switch = pcie_switch

    def perform_preconditioning(self, io_flows):
        for i, flow in enumerate(io_flows):
            if hasattr(flow, 'initial_occupancy_percentage'):
                occupancy_ratio = flow.initial_occupancy_percentage / 100.0
                address_dist = getattr(flow, 'address_distribution', "RANDOM_UNIFORM")
                # Fix attribute names to match IOFlowParameterSet
                hot_ratio = getattr(flow, 'percentage_of_hot_region', 10) / 100.0
                working_set_ratio = getattr(flow, 'working_set_percentage', 85) / 100.0
                
                self.firmware.perform_preconditioning(
                    occupancy_ratio, i, 
                    address_distribution=address_dist,
                    hot_ratio=hot_ratio,
                    working_set_ratio=working_set_ratio
                )
