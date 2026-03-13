from mqsim.sim.sim_object import SimObject
from mqsim.ssd.flash_block_manager import FlashBlockManager
from mqsim.ssd.mapping_unit import PageLevelAddressMapping
from mqsim.ssd.tsu_outoforder import TSUOutOfOrder
from mqsim.ssd.gc_and_wl_unit import GCUnit
from mqsim.ssd.nvm_transaction import NVMTransaction, TransactionType, TransactionSource
from mqsim.utils.random_generator import RandomGenerator

class FTL(SimObject):
    def __init__(self, id, channel_no, chip_no_per_channel, die_no_per_chip, 
                 plane_no_per_die, block_no_per_plane, page_no_per_block, 
                 page_size_in_sectors, over_provisioning_ratio, seed):
        super().__init__(id)
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
        self.tsu = TSUOutOfOrder(f"{id}.TSU", channel_no, chip_no_per_channel)

        # 4. Initialize GC and WL Unit
        self.gc_and_wl_unit = GCUnit(
            f"{id}.GCUnit", self.block_manager, self.tsu, "RGA"
        )
        self.block_manager.set_gc_unit(self.gc_and_wl_unit)

        self.phy = None
        self.data_cache_manager = None
        self.host_interface = None

    def set_host_interface(self, host_interface):
        self.host_interface = host_interface
        self.tsu.host_interface = host_interface

    def segment_user_request(self, user_request):
        """
        Breaks a host-level request into page-sized NVM transactions.
        """
        lsa = user_request.lsa
        size = user_request.size_in_sectors
        
        transactions = []
        
        # Calculate the starting LPA and offset
        current_lsa = lsa
        remaining_size = size
        
        self.tsu.prepare_for_transaction_submit()
        
        while remaining_size > 0:
            lpa = current_lsa // self.page_size_in_sectors
            sectors_in_this_page = min(remaining_size, 
                                       self.page_size_in_sectors - (current_lsa % self.page_size_in_sectors))
            
            tr = NVMTransaction(
                stream_id=user_request.stream_id,
                transaction_type=user_request.type,
                source=TransactionSource.USERIO,
                lpa=lpa,
                user_request=user_request
            )
            
            # Simple Static Plane Allocation CWDP (Channel-Way-Die-Plane)
            # Ported simplified allocation from C++
            channel_id = lpa % self.channel_no
            chip_id = (lpa // self.channel_no) % self.chip_no_per_channel
            die_id = (lpa // (self.channel_no * self.chip_no_per_channel)) % self.die_no_per_chip
            plane_id = (lpa // (self.channel_no * self.chip_no_per_channel * self.die_no_per_chip)) % self.plane_no_per_die
            
            tr.address = {
                "channel": channel_id,
                "chip": chip_id,
                "die": die_id,
                "plane": plane_id,
                "block": 0, # To be allocated by block manager if write
                "page": 0
            }
            
            if tr.type == "WRITE":
                # Allocate a new PPA
                allocated_addr = self.block_manager.allocate_page_for_user_write(tr.stream_id, tr.address)
                tr.address = allocated_addr
                tr.ppa = 0 # Dummy PPA
                self.address_mapping_unit.update_mapping_info(tr.stream_id, tr.lpa, tr.ppa)
            else:
                # Read: Look up PPA
                tr.ppa = self.address_mapping_unit.get_ppa(tr.stream_id, tr.lpa)
                if tr.ppa == -1:
                    # Not written yet, return dummy data (still takes time)
                    pass
            
            transactions.append(tr)
            user_request.transaction_list.append(tr)
            
            self.tsu.submit_transaction(tr)
            
            current_lsa += sectors_in_this_page
            remaining_size -= sectors_in_this_page
            
        self.tsu.schedule()
        
        # Manually trigger servicing for each channel/chip if they are IDLE
        for c in range(self.channel_no):
            for i in range(self.chip_no_per_channel):
                chip = self.phy.get_chip(c, i)
                if chip.status == 0: # IDLE
                    self.tsu.handle_chip_idle_signal(chip)
                    
        return transactions

    def execute_sim_event(self, event):
        pass
