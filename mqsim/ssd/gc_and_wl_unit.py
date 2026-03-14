from mqsim.sim.sim_object import SimObject

class GCTransaction:
    def __init__(self, type, source, address, related_write=None, related_read=None, related_erase=None):
        self.type = type
        self.source = source
        self.address = address
        self.related_write = related_write
        self.related_read = related_read
        self.related_erase = related_erase
        self.page_movement_activities = []

class GCUnit(SimObject):
    def __init__(self, id, block_manager, tsu=None, 
                 block_selection_policy="GREEDY",
                 gc_threshold=0.1, gc_hard_threshold=0.05,
                 rga_set_size=8, seed=432):
        super().__init__(id)
        self.block_manager = block_manager
        self.tsu = tsu
        self.block_selection_policy = block_selection_policy
        self.gc_threshold = gc_threshold # Ratio of free blocks
        self.gc_hard_threshold = gc_hard_threshold
        self.rga_set_size = rga_set_size
        import random
        self.rng = random.Random(seed)
        
        # Track ongoing GC operations to manage "urgent" mode
        self.ongoing_gc_per_plane = {} # Plane -> count

    def is_urgent(self, plane_address):
        plane_record = self.block_manager._get_plane_bookkeeping(plane_address)
        free_blocks = len(plane_record.free_block_pool)
        total_blocks = len(plane_record.blocks)
        
        # Urgent if below hard threshold
        return free_blocks < (total_blocks * self.gc_hard_threshold)

    def select_victim_block(self, plane_address):
        plane_record = self.block_manager._get_plane_bookkeeping(plane_address)
        
        victim_block_id = -1
        max_invalid_pages = -1
        
        blocks_to_check = []
        if self.block_selection_policy == "GREEDY":
            blocks_to_check = plane_record.blocks
        elif self.block_selection_policy == "RGA":
            # Randomly select a subset of blocks that are not free and not write frontiers
            potential_blocks = [b for b in plane_record.blocks 
                               if b.block_id not in plane_record.free_block_pool]
            if plane_record.data_wf:
                potential_blocks = [b for b in potential_blocks if b.block_id != plane_record.data_wf.block_id]
            if plane_record.translation_wf:
                potential_blocks = [b for b in potential_blocks if b.block_id != plane_record.translation_wf.block_id]
                
            if len(potential_blocks) > self.rga_set_size:
                blocks_to_check = self.rng.sample(potential_blocks, self.rga_set_size)
            else:
                blocks_to_check = potential_blocks

        for block in blocks_to_check:
            # 1. Skip if it's the current write frontier
            if plane_record.data_wf and block.block_id == plane_record.data_wf.block_id:
                continue
            if plane_record.translation_wf and block.block_id == plane_record.translation_wf.block_id:
                continue
            
            # 2. Skip if it's currently in the free pool
            if block.block_id in plane_record.free_block_pool:
                continue

            # 3. Greedy part: select block with most invalid pages
            if block.invalid_page_count > max_invalid_pages:
                max_invalid_pages = block.invalid_page_count
                victim_block_id = block.block_id
                    
        return victim_block_id

    def check_gc_required(self, plane_address):
        plane_record = self.block_manager._get_plane_bookkeeping(plane_address)
        free_blocks = len(plane_record.free_block_pool)
        total_blocks = len(plane_record.blocks)
        
        # Threshold-based trigger
        if free_blocks > (total_blocks * self.gc_threshold):
            return None

        victim_block_id = self.select_victim_block(plane_address)
        if victim_block_id == -1:
            return None
            
        block = plane_record.blocks[victim_block_id]
        
        # Only execute GC if we have a TSU attached
        if self.tsu:
            self.tsu.prepare_for_transaction_submit()
            
            # Create Erase Transaction
            erase_addr = dict(plane_address, block=victim_block_id)
            gc_erase_tr = GCTransaction("ERASE", "GC_WL", erase_addr)
            
            # Check for valid pages that need moving
            valid_pages_count = block.current_page_write_index - block.invalid_page_count
            if valid_pages_count > 0:
                for page_id in range(block.current_page_write_index):
                    # If page is valid (not in the invalid bitmap)
                    if not block.invalid_page_bitmap[page_id]:
                        page_addr = dict(erase_addr, page=page_id)
                        
                        gc_read = GCTransaction("READ", "GC_WL", page_addr)
                        gc_write = GCTransaction("WRITE", "GC_WL", page_addr, related_read=gc_read, related_erase=gc_erase_tr)
                        gc_read.related_write = gc_write
                        
                        gc_erase_tr.page_movement_activities.append(gc_write)
                        
                        # Only submit read; write happens after read finishes
                        self.tsu.submit_transaction(gc_read)
            
            self.tsu.submit_transaction(gc_erase_tr)
            self.tsu.schedule()
            
        return victim_block_id

    def execute_sim_event(self, event):
        pass
