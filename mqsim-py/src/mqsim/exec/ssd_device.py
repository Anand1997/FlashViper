from mqsim.ssd.ftl import FTL

class MockHostInterface:
    def __init__(self):
        self.pcie_switch = None

class MockCacheManager:
    pass

class SSDDevice:
    def __init__(self, parameters, io_flows):
        self.parameters = parameters
        self.io_flows = io_flows
        self.memory_type = parameters.memory_type
        self.channel_count = parameters.flash_channel_count
        
        # 1. Host Interface
        self.host_interface = MockHostInterface()
        
        # 2. Data Cache Manager
        self.cache_manager = MockCacheManager()
        
        # 3. NVM Firmware (FTL)
        # Using simplified parameters for this basic porting stage
        self.firmware = FTL(
            channel_no=self.channel_count,
            chip_no_per_channel=getattr(parameters, 'chip_no_per_channel', 4),
            die_no_per_chip=getattr(parameters.flash_params, 'die_no_per_chip', 2),
            plane_no_per_die=getattr(parameters.flash_params, 'plane_no_per_die', 2),
            block_no_per_plane=getattr(parameters.flash_params, 'block_no_per_plane', 2048),
            page_no_per_block=getattr(parameters.flash_params, 'page_no_per_block', 256),
            page_size_in_sectors=getattr(parameters.flash_params, 'page_capacity', 8192) // 512,
            over_provisioning_ratio=getattr(parameters, 'overprovisioning_ratio', 0.07),
            seed=getattr(parameters, 'seed', 321)
        )
        
        self.phy = None
        self.channels = []

    def attach_to_host(self, pcie_switch):
        self.host_interface.pcie_switch = pcie_switch
