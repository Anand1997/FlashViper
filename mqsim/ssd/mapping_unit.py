from collections import OrderedDict

class CMTEntryStatus:
    FREE = 0
    WAITING = 1
    VALID = 2

class CMTSlot:
    def __init__(self, ppa=-1, status=CMTEntryStatus.FREE, dirty=False):
        self.ppa = ppa
        self.status = status
        self.dirty = dirty
        # In MQSim, it also tracks WrittenStateBitmap, but we simplify for now

class CachedMappingTable:
    def __init__(self, capacity):
        self.capacity = capacity
        # Using OrderedDict to implement LRU efficiently
        # Key: LPA, Value: CMTSlot
        self.slots = OrderedDict()

    def exists(self, lpa):
        if lpa in self.slots:
            # Move to end (most recently used)
            self.slots.move_to_end(lpa)
            return True
        return False

    def retrieve_ppa(self, lpa):
        if lpa in self.slots:
            self.slots.move_to_end(lpa)
            return self.slots[lpa].ppa
        return -1

    def insert(self, lpa, ppa, dirty=False, status=CMTEntryStatus.VALID):
        if len(self.slots) >= self.capacity and lpa not in self.slots:
            # Eviction should be handled by the caller who knows if it's dirty
            pass
        
        slot = CMTSlot(ppa, status, dirty)
        self.slots[lpa] = slot
        self.slots.move_to_end(lpa)
        return slot

    def evict_lru(self):
        if not self.slots:
            return None, None
        lpa, slot = self.slots.popitem(last=False)
        return lpa, slot

    def is_dirty(self, lpa):
        if lpa in self.slots:
            return self.slots[lpa].dirty
        return False

class AddressMappingDomain:
    def __init__(self, cmt_capacity, no_of_logical_pages):
        self.cmt = CachedMappingTable(cmt_capacity)
        self.no_of_logical_pages = no_of_logical_pages
        # Global Mapping Table: LPA -> PPA
        self.gmt = {} 
        # Global Translation Directory: MVPN -> MPPN
        self.gtd = {}
        
        # Transactions waiting for mapping data to be fetched from flash
        self.waiting_unmapped_read_transactions = {} # LPA -> list of transactions
        self.waiting_unmapped_program_transactions = {} # LPA -> list of transactions

    def get_ppa(self, lpa, ideal=False):
        if ideal:
            return self.gmt.get(lpa, -1)
            
        if self.cmt.exists(lpa):
            return self.cmt.retrieve_ppa(lpa)
        return -1

    def update_mapping_info_for_preconditioning(self, lpa, ppa):
        self.gmt[lpa] = ppa
        # During preconditioning, we assume mapping is ideal/already persistent
        # and doesn't need to be in CMT necessarily unless we want to simulate 
        # it being there. In MQSim, it typically just populates GMT.
        # But we can insert into CMT to make it "hot".
        self.cmt.insert(lpa, ppa, dirty=False)

    def update_mapping_info(self, lpa, ppa, ideal=False):
        if lpa >= self.no_of_logical_pages:
            raise ValueError(f"LPA {lpa} exceeds logical capacity {self.no_of_logical_pages}")
        
        self.gmt[lpa] = ppa
        if not ideal:
            self.cmt.insert(lpa, ppa, dirty=True)

class PageLevelAddressMapping:
    def __init__(self, no_of_logical_pages, cmt_capacity=1024, stream_count=1, ideal=False, scheme="CWDP"):
        self.no_of_logical_pages = no_of_logical_pages
        self.cmt_capacity = cmt_capacity
        self.ideal = ideal
        self.scheme = scheme
        
        # Support multiple domains for multi-stream SSDs
        self.domains = [AddressMappingDomain(cmt_capacity, no_of_logical_pages) for _ in range(stream_count)]

    def get_ppa(self, stream_id, lpa):
        return self.domains[stream_id].get_ppa(lpa, self.ideal)

    def update_mapping_info(self, stream_id, lpa, ppa):
        self.domains[stream_id].update_mapping_info(lpa, ppa, self.ideal)

    def query_cmt(self, stream_id, lpa):
        if self.ideal:
            return True
        return self.domains[stream_id].cmt.exists(lpa)

    def get_physical_address(self, lpa, channel_no, chip_no, die_no, plane_no):
        """
        Calculates physical address components based on the allocation scheme.
        Common MQSim schemes: CWDP, CDWP, WDCP, etc.
        """
        if self.scheme == "CWDP":
            channel_id = lpa % channel_no
            chip_id = (lpa // channel_no) % chip_no
            die_id = (lpa // (channel_no * chip_no)) % die_no
            plane_id = (lpa // (channel_no * chip_no * die_no)) % plane_no
        elif self.scheme == "CDWP":
            channel_id = lpa % channel_no
            die_id = (lpa // channel_no) % die_no
            chip_id = (lpa // (channel_no * die_no)) % chip_no
            plane_id = (lpa // (channel_no * die_no * chip_no)) % plane_no
        elif self.scheme == "WDCP":
            chip_id = lpa % chip_no
            die_id = (lpa // chip_no) % die_no
            channel_id = (lpa // (chip_no * die_no)) % channel_no
            plane_id = (lpa // (chip_no * die_no * channel_no)) % plane_no
        else: # Default to CWDP
            channel_id = lpa % channel_no
            chip_id = (lpa // channel_no) % chip_no
            die_id = (lpa // (channel_no * chip_no)) % die_no
            plane_id = (lpa // (channel_no * chip_no * die_no)) % plane_no
            
        return {
            "channel": channel_id,
            "chip": chip_id,
            "die": die_id,
            "plane": plane_id
        }

    def allocate_page_for_translation_write(self, stream_id, lpa):
        # This will be called by FTL when a dirty CMT entry is evicted
        pass
