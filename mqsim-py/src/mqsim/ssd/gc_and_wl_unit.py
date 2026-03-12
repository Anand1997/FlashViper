from mqsim.sim.sim_object import SimObject

class GCUnit(SimObject):
    def __init__(self, id, block_manager, block_selection_policy="GREEDY"):
        super().__init__(id)
        self.block_manager = block_manager
        self.block_selection_policy = block_selection_policy

    def select_victim_block(self, plane_address):
        plane_record = self.block_manager._get_plane_bookkeeping(plane_address)
        
        victim_block_id = -1
        max_invalid_pages = -1
        
        if self.block_selection_policy == "GREEDY":
            for block in plane_record.blocks:
                # In MQSim, we don't select the current write frontier as a victim
                if plane_record.data_wf and block.block_id == plane_record.data_wf.block_id:
                    continue
                
                # Also don't select already free blocks or blocks being erased
                if block.block_id in plane_record.free_block_pool:
                    continue

                if block.invalid_page_count > max_invalid_pages:
                    max_invalid_pages = block.invalid_page_count
                    victim_block_id = block.block_id
                    
        return victim_block_id

    def execute_sim_event(self, event):
        pass
