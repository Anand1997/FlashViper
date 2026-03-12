from mqsim.ssd.flash_block_manager import FlashBlockManager
from mqsim.ssd.mapping_unit import PageLevelAddressMapping
from mqsim.ssd.tsu_base import TSUBase
from mqsim.utils.random_generator import RandomGenerator

class SimpleTSU(TSUBase):
    def schedule(self):
        # A simple pass-through scheduler for basic functionality
        for trans in self.transaction_receive_slots:
            if self._transaction_is_ready(trans):
                self.transaction_dispatch_slots.append(trans)
        self.transaction_receive_slots.clear()

    def service_read_transaction(self, chip): pass
    def service_write_transaction(self, chip): pass
    def service_erase_transaction(self, chip): pass

class FTL:
    def __init__(self, channel_no, chip_no_per_channel, die_no_per_chip, 
                 plane_no_per_die, block_no_per_plane, page_no_per_block, 
                 page_size_in_sectors, over_provisioning_ratio, seed):
        
        self.channel_no = channel_no
        self.chip_no_per_channel = chip_no_per_channel
        self.die_no_per_chip = die_no_per_chip
        self.plane_no_per_die = plane_no_per_die
        self.block_no_per_plane = block_no_per_plane
        self.page_no_per_block = page_no_per_block
        self.page_size_in_sectors = page_size_in_sectors
        self.over_provisioning_ratio = over_provisioning_ratio
        
        self.random_generator = RandomGenerator(seed)

        # 1. Initialize Block Manager
        self.block_manager = FlashBlockManager(
            channel_no, chip_no_per_channel, die_no_per_chip, 
            plane_no_per_die, block_no_per_plane, page_no_per_block
        )

        # 2. Initialize Mapping Unit
        total_physical_pages = (channel_no * chip_no_per_channel * 
                                die_no_per_chip * plane_no_per_die * 
                                block_no_per_plane * page_no_per_block)
        
        no_of_logical_pages = int(total_physical_pages * (1.0 - over_provisioning_ratio))
        self.address_mapping_unit = PageLevelAddressMapping(no_of_logical_pages)

        # 3. Initialize Transaction Scheduling Unit (TSU)
        self.tsu = SimpleTSU()
