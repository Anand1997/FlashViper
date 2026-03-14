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
                 page_size_in_sectors, over_provisioning_ratio, seed,
                 cmt_capacity=1024, stream_count=1):
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
        self.address_mapping_unit = PageLevelAddressMapping(no_of_logical_pages, cmt_capacity, stream_count)

        # 3. Initialize Transaction Scheduling Unit (TSU)
        self.tsu = TSUOutOfOrder(f"{id}.TSU", channel_no, chip_no_per_channel)
        self.tsu.ftl = self

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

    def perform_preconditioning(self, occupancy_ratio, stream_id):
        """
        Fills the mapping table and physical blocks to reach target occupancy.
        Bypasses TSU and PHY for speed.
        """
        if occupancy_ratio <= 0:
            return
            
        no_of_logical_pages = self.address_mapping_unit.no_of_logical_pages
        pages_to_write = int(no_of_logical_pages * occupancy_ratio)
        
        print(f"Preconditioning Stream {stream_id}: Writing {pages_to_write} pages ({occupancy_ratio*100}% occupancy)")
        
        # Use a random sample of LPAs
        import random
        all_lpas = list(range(no_of_logical_pages))
        target_lpas = random.sample(all_lpas, pages_to_write)
        
        for lpa in target_lpas:
            # Static allocation to find a plane
            channel_id = lpa % self.channel_no
            chip_id = (lpa // self.channel_no) % self.chip_no_per_channel
            die_id = (lpa // (self.channel_no * self.chip_no_per_channel)) % self.die_no_per_chip
            plane_id = (lpa // (self.channel_no * self.chip_no_per_channel * self.die_no_per_chip)) % self.plane_no_per_die
            
            address = {
                "channel": channel_id,
                "chip": chip_id,
                "die": die_id,
                "plane": plane_id
            }
            
            # Allocate physical page
            allocated_addr = self.block_manager.allocate_page_for_preconditioning(stream_id, address)
            
            # Update mapping
            self.address_mapping_unit.domains[stream_id].update_mapping_info_for_preconditioning(lpa, 0) # Dummy PPA

    def allocate_page_for_translation_write(self, stream_id, lpa):
        # Find a suitable plane (Static allocation)
        channel_id = lpa % self.channel_no
        chip_id = (lpa // self.channel_no) % self.chip_no_per_channel
        die_id = (lpa // (self.channel_no * self.chip_no_per_channel)) % self.die_no_per_chip
        plane_id = (lpa // (self.channel_no * self.chip_no_per_channel * self.die_no_per_chip)) % self.plane_no_per_die
        
        target_addr = {
            "channel": channel_id,
            "chip": chip_id,
            "die": die_id,
            "plane": plane_id
        }
        
        return self.block_manager.allocate_page_for_translation_write(stream_id, target_addr)

    def segment_user_request(self, user_request):
        """
        Breaks a host-level request into page-sized NVM transactions.
        Handles CMT misses and evictions.
        """
        lsa = user_request.lsa
        size = user_request.size_in_sectors
        
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
            
            # 1. CMT Lookup
            if not self.address_mapping_unit.query_cmt(tr.stream_id, tr.lpa):
                # MISS: Generate mapping read
                # In MQSim, multiple transactions for the same LPA wait for one mapping read
                domain = self.address_mapping_unit.domains[tr.stream_id]
                if tr.lpa not in domain.waiting_unmapped_read_transactions:
                    domain.waiting_unmapped_read_transactions[tr.lpa] = []
                    
                    # Generate Mapping Read Transaction
                    mapping_tr = NVMTransaction(
                        stream_id=tr.stream_id,
                        transaction_type=TransactionType.READ,
                        source=TransactionSource.MAPPING,
                        lpa=tr.lpa
                    )
                    # For mapping pages, we use a different allocation or static 
                    # Simplified: same static plane as data
                    m_channel = tr.lpa % self.channel_no
                    m_chip = (tr.lpa // self.channel_no) % self.chip_no_per_channel
                    mapping_tr.address = {
                        "channel": m_channel, "chip": m_chip, "die": 0, "plane": 0, "block": 0, "page": 0
                    }
                    
                    # Handle Eviction if CMT is full
                    if len(domain.cmt.slots) >= domain.cmt.capacity:
                        evicted_lpa, evicted_slot = domain.cmt.evict_lru()
                        if evicted_slot and evicted_slot.dirty:
                            # Generate Mapping Writeback
                            wb_tr = NVMTransaction(
                                stream_id=tr.stream_id,
                                transaction_type=TransactionType.WRITE,
                                source=TransactionSource.MAPPING,
                                lpa=evicted_lpa
                            )
                            wb_tr.address = self.allocate_page_for_translation_write(tr.stream_id, evicted_lpa)
                            self.tsu.submit_transaction(wb_tr)

                    self.tsu.submit_transaction(mapping_tr)
                
                domain.waiting_unmapped_read_transactions[tr.lpa].append(tr)
                tr.suspend_required = True # Mark that it shouldn't be scheduled yet
            
            # 2. Address Allocation
            channel_id = lpa % self.channel_no
            chip_id = (lpa // self.channel_no) % self.chip_no_per_channel
            die_id = (lpa // (self.channel_no * self.chip_no_per_channel)) % self.die_no_per_chip
            plane_id = (lpa // (self.channel_no * self.chip_no_per_channel * self.die_no_per_chip)) % self.plane_no_per_die
            
            tr.address = {
                "channel": channel_id,
                "chip": chip_id,
                "die": die_id,
                "plane": plane_id,
                "block": 0, "page": 0
            }
            
            if tr.type == "WRITE":
                allocated_addr = self.block_manager.allocate_page_for_user_write(tr.stream_id, tr.address)
                tr.address = allocated_addr
                tr.ppa = 0 # Dummy
                self.address_mapping_unit.update_mapping_info(tr.stream_id, tr.lpa, tr.ppa)
            else:
                tr.ppa = self.address_mapping_unit.get_ppa(tr.stream_id, tr.lpa)
            
            user_request.transaction_list.append(tr)
            if not tr.suspend_required:
                self.tsu.submit_transaction(tr)
            
            current_lsa += sectors_in_this_page
            remaining_size -= sectors_in_this_page
            
        self.tsu.schedule()
                    
        return user_request.transaction_list

    def handle_transaction_finished(self, transaction):
        if transaction.source == TransactionSource.MAPPING:
            domain = self.address_mapping_unit.domains[transaction.stream_id]
            if transaction.type == TransactionType.READ:
                # Mapping entry fetched from flash
                ppa = self.address_mapping_unit.get_ppa(transaction.stream_id, transaction.lpa) # This might still return -1 if not in GMT
                
                # If it's already in CMT and dirty, don't clear the dirty bit
                is_dirty = domain.cmt.is_dirty(transaction.lpa)
                domain.cmt.insert(transaction.lpa, ppa, dirty=is_dirty)
                
                # Release waiting transactions
                if transaction.lpa in domain.waiting_unmapped_read_transactions:
                    waiting_txs = domain.waiting_unmapped_read_transactions.pop(transaction.lpa)
                    for tr in waiting_txs:
                        tr.suspend_required = False
                        # If it's a read, we need to update its PPA now that CMT is populated
                        if tr.type == TransactionType.READ:
                            tr.ppa = domain.cmt.retrieve_ppa(tr.lpa)
                        self.tsu.submit_transaction(tr)
                    self.tsu.schedule()
            else:
                # Mapping writeback finished
                # In MQSim, we might need to update GTD or just mark as clean
                pass

    def execute_sim_event(self, event):
        pass
