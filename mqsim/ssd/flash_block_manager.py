class BlockPoolSlot:
    def __init__(self, block_id, page_no_per_block):
        self.block_id = block_id
        self.current_page_write_index = 0
        self.invalid_page_count = 0
        self.erase_count = 0
        # Simple boolean list to track valid/invalid pages
        self.invalid_page_bitmap = [False] * page_no_per_block

class PlaneBookKeeping:
    def __init__(self, block_no_per_plane, page_no_per_block):
        self.blocks = [BlockPoolSlot(i, page_no_per_block) for i in range(block_no_per_plane)]
        self.free_block_pool = list(range(block_no_per_plane))
        self.data_wf = None  # Data Write Frontier (the active block)
        self.translation_wf = None # Translation Write Frontier

    def get_free_block(self):
        if not self.free_block_pool:
            # Trigger GC if needed? For now just raise error
            raise RuntimeError("No free blocks available!")
        block_id = self.free_block_pool.pop(0)
        return self.blocks[block_id]

class FlashBlockManager:
    def __init__(self, channel_count, chip_no_per_channel, die_no_per_chip, 
                 plane_no_per_die, block_no_per_plane, page_no_per_block):
        
        self.page_no_per_block = page_no_per_block
        self.gc_unit = None
        
        # Initialize the 4D array: Channel -> Chip -> Die -> Plane -> PlaneBookKeeping
        self.plane_manager = [[[[PlaneBookKeeping(block_no_per_plane, page_no_per_block) 
                                 for _ in range(plane_no_per_die)] 
                                for _ in range(die_no_per_chip)] 
                               for _ in range(chip_no_per_channel)] 
                              for _ in range(channel_count)]

    def set_gc_unit(self, gc_unit):
        self.gc_unit = gc_unit

    def _get_plane_bookkeeping(self, address):
        return self.plane_manager[address["channel"]][address["chip"]][address["die"]][address["plane"]]

    def allocate_page_for_translation_write(self, stream_id, address):
        plane_record = self._get_plane_bookkeeping(address)
        
        if plane_record.translation_wf is None or plane_record.translation_wf.current_page_write_index == self.page_no_per_block:
            plane_record.translation_wf = plane_record.get_free_block()
        
        wf = plane_record.translation_wf
        allocated_page_id = wf.current_page_write_index
        wf.current_page_write_index += 1
        
        return {
            "channel": address["channel"],
            "chip": address["chip"],
            "die": address["die"],
            "plane": address["plane"],
            "block": wf.block_id,
            "page": allocated_page_id
        }

    def allocate_page_for_user_write(self, stream_id, address):
        plane_record = self._get_plane_bookkeeping(address)
        
        # If there is no active write block, or the active block is full, get a new one
        if plane_record.data_wf is None or plane_record.data_wf.current_page_write_index == self.page_no_per_block:
            plane_record.data_wf = plane_record.get_free_block()
        
        wf = plane_record.data_wf
        allocated_page_id = wf.current_page_write_index
        wf.current_page_write_index += 1
        
        # Return a copy of the address updated with block and page
        return {
            "channel": address["channel"],
            "chip": address["chip"],
            "die": address["die"],
            "plane": address["plane"],
            "block": wf.block_id,
            "page": allocated_page_id
        }

    def invalidate_page(self, address, block_id, page_id):
        plane_record = self._get_plane_bookkeeping(address)
        block = plane_record.blocks[block_id]
        
        if not block.invalid_page_bitmap[page_id]:
            block.invalid_page_bitmap[page_id] = True
            block.invalid_page_count += 1

    def get_invalid_page_count(self, address, block_id):
        plane_record = self._get_plane_bookkeeping(address)
        return plane_record.blocks[block_id].invalid_page_count
