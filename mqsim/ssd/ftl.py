from mqsim.sim.sim_object import SimObject
from mqsim.ssd.flash_block_manager import FlashBlockManager
from mqsim.ssd.mapping_unit import PageLevelAddressMapping
from mqsim.ssd.tsu_outoforder import TSUOutOfOrder
from mqsim.ssd.gc_and_wl_unit import GCUnit
from mqsim.ssd.nvm_transaction import NVMTransaction, TransactionType, TransactionSource
from mqsim.utils.random_generator import RandomGenerator
from mqsim.sim.engine import Engine

class FTL(SimObject):
    def __init__(self, id, channel_no, chip_no_per_channel, die_no_per_chip, 
                 plane_no_per_die, block_no_per_plane, page_no_per_block, 
                 page_size_in_sectors, over_provisioning_ratio, seed,
                 cmt_capacity=1024, stream_count=1, scheme="CWDP", ideal=False):
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
        self.address_mapping_unit = PageLevelAddressMapping(no_of_logical_pages, cmt_capacity, stream_count, scheme=scheme, ideal=ideal)

        # 3. Initialize Transaction Scheduling Unit (TSU)
        self.tsu = TSUOutOfOrder(f"{id}.TSU", channel_no, chip_no_per_channel, stream_count=stream_count)
        self.tsu.ftl = self

        # 4. Initialize GC and WL Unit
        self.gc_and_wl_unit = GCUnit(
            f"{id}.GCUnit", self.block_manager, self.tsu, 
            block_selection_policy="RGA",
            gc_threshold=0.1, gc_hard_threshold=0.05
        )
        self.block_manager.set_gc_unit(self.gc_and_wl_unit)

        self.phy = None
        self.data_cache_manager = None
        self.host_interface = None

        # MQSim Style Stats
        self.STAT_issued_flash_read_cmd = 0
        self.STAT_issued_flash_program_cmd = 0
        self.STAT_issued_flash_erase_cmd = 0
        self.STAT_issued_flash_read_cmd_for_mapping = 0
        self.STAT_issued_flash_program_cmd_for_mapping = 0
        self.STAT_cmt_hits = 0
        self.STAT_cmt_misses = 0
        self.STAT_total_cmt_queries = 0

    def set_host_interface(self, host_interface):
        self.host_interface = host_interface
        self.tsu.host_interface = host_interface

    def perform_preconditioning(self, occupancy_ratio, stream_id, 
                                address_distribution="RANDOM_UNIFORM", 
                                hot_ratio=0.1, working_set_ratio=0.8):
        """
        Fills the mapping table and physical blocks to reach target occupancy,
        matching the synthetic workload distribution.
        """
        if occupancy_ratio <= 0:
            return
            
        no_of_logical_pages = self.address_mapping_unit.no_of_logical_pages
        # Only precondition within the working set
        working_set_pages = int(no_of_logical_pages * working_set_ratio)
        pages_to_write = int(no_of_logical_pages * occupancy_ratio)
        
        # Ensure we don't try to write more than the working set
        pages_to_write = min(pages_to_write, working_set_pages)
        
        print(f"Preconditioning Stream {stream_id}: Writing {pages_to_write} pages ({occupancy_ratio*100}% occupancy, {address_distribution})")
        
        target_lpas = []
        import random
        
        if address_distribution == "RANDOM_HOTCOLD":
            # MQSim approach: Allocate 95% of preconditioning writes to the hot region 
            # until it's full or we reach the 95% target.
            hot_region_pages = int(working_set_pages * hot_ratio)
            cold_region_pages = working_set_pages - hot_region_pages
            
            # Target 95% of writes to hot region
            hot_writes_target = int(pages_to_write * 0.95)
            # But can't write more than hot region size
            hot_writes = min(hot_writes_target, hot_region_pages)
            cold_writes = pages_to_write - hot_writes
            
            # Hot LPAs
            target_lpas.extend(random.sample(range(0, hot_region_pages), hot_writes))
            # Cold LPAs
            if cold_region_pages > 0:
                target_lpas.extend(random.sample(range(hot_region_pages, working_set_pages), min(cold_writes, cold_region_pages)))
        else:
            # UNIFORM or STREAMING
            target_lpas = random.sample(range(0, working_set_pages), pages_to_write)
        
        for lpa in target_lpas:
            # Use configurable allocation scheme
            address = self.address_mapping_unit.get_physical_address(
                lpa, self.channel_no, self.chip_no_per_channel, self.die_no_per_chip, self.plane_no_per_die
            )
            
            # Allocate physical page
            allocated_addr = self.block_manager.allocate_page_for_preconditioning(stream_id, address)
            
            # Check for overwrite and invalidate old page
            old_ppa = self.address_mapping_unit.get_ppa(stream_id, lpa)
            if old_ppa != -1:
                pass

            # Update mapping
            self.address_mapping_unit.domains[stream_id].update_mapping_info_for_preconditioning(lpa, 0) # Dummy PPA

    def allocate_page_for_translation_write(self, stream_id, lpa):
        # Use configurable allocation scheme
        target_addr = self.address_mapping_unit.get_physical_address(
            lpa, self.channel_no, self.chip_no_per_channel, self.die_no_per_chip, self.plane_no_per_die
        )
        
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
            self.STAT_total_cmt_queries += 1
            if not self.address_mapping_unit.query_cmt(tr.stream_id, tr.lpa):
                # MISS: Generate mapping read
                self.STAT_cmt_misses += 1
                domain = self.address_mapping_unit.domains[tr.stream_id]
                if tr.lpa not in domain.waiting_unmapped_read_transactions:
                    domain.waiting_unmapped_read_transactions[tr.lpa] = []
                    
                    # Generate Mapping Read Transaction
                    self.STAT_issued_flash_read_cmd_for_mapping += 1
                    mapping_tr = NVMTransaction(
                        stream_id=tr.stream_id,
                        transaction_type=TransactionType.READ,
                        source=TransactionSource.MAPPING,
                        lpa=tr.lpa
                    )
                    # For mapping pages, we use the same scheme
                    mapping_tr.address = self.address_mapping_unit.get_physical_address(
                        tr.lpa, self.channel_no, self.chip_no_per_channel, self.die_no_per_chip, self.plane_no_per_die
                    )
                    mapping_tr.address.update({"block": 0, "page": 0})
                    
                    # Handle Eviction if CMT is full
                    if len(domain.cmt.slots) >= domain.cmt.capacity:
                        evicted_lpa, evicted_slot = domain.cmt.evict_lru()
                        if evicted_slot and evicted_slot.dirty:
                            # Generate Mapping Writeback
                            self.STAT_issued_flash_program_cmd_for_mapping += 1
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
            else:
                self.STAT_cmt_hits += 1
            
            # 2. Address Allocation
            tr.address = self.address_mapping_unit.get_physical_address(
                lpa, self.channel_no, self.chip_no_per_channel, self.die_no_per_chip, self.plane_no_per_die
            )
            tr.address.update({"block": 0, "page": 0})
            
            if tr.type == "WRITE":
                self.STAT_issued_flash_program_cmd += 1
                allocated_addr = self.block_manager.allocate_page_for_user_write(tr.stream_id, tr.address)
                tr.address = allocated_addr
                tr.ppa = 0 # Dummy
                self.address_mapping_unit.update_mapping_info(tr.stream_id, tr.lpa, tr.ppa)
            else:
                self.STAT_issued_flash_read_cmd += 1
                tr.ppa = self.address_mapping_unit.get_ppa(tr.stream_id, tr.lpa)
            
            user_request.transaction_list.append(tr)
            if not tr.suspend_required:
                self.tsu.submit_transaction(tr)
            
            current_lsa += sectors_in_this_page
            remaining_size -= sectors_in_this_page
            
        self.tsu.schedule()
                    
        return user_request.transaction_list

    def report_results_in_xml(self, name_prefix, xml_writer):
        xmlwriter = xml_writer
        tmp = name_prefix + ".FTL"
        xmlwriter.write_open_tag(tmp)
        
        xmlwriter.write_attribute_string("Issued_Flash_Read_CMD", self.STAT_issued_flash_read_cmd)
        xmlwriter.write_attribute_string("Issued_Flash_Program_CMD", self.STAT_issued_flash_program_cmd)
        xmlwriter.write_attribute_string("Issued_Flash_Erase_CMD", self.STAT_issued_flash_erase_cmd)
        xmlwriter.write_attribute_string("Issued_Flash_Read_CMD_For_Mapping", self.STAT_issued_flash_read_cmd_for_mapping)
        xmlwriter.write_attribute_string("Issued_Flash_Program_CMD_For_Mapping", self.STAT_issued_flash_program_cmd_for_mapping)
        xmlwriter.write_attribute_string("CMT_Hits", self.STAT_cmt_hits)
        xmlwriter.write_attribute_string("CMT_Misses", self.STAT_cmt_misses)
        xmlwriter.write_attribute_string("Total_CMT_Queries", self.STAT_total_cmt_queries)
        
        xmlwriter.write_close_tag()

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
                pass

    def execute_sim_event(self, event):
        if event.type == "SEGMENT":
            user_request = event.parameters
            self.segment_user_request(user_request)
