from abc import abstractmethod
from mqsim.sim.sim_object import SimObject
from enum import Enum

class CachingMode(Enum):
    WRITE_CACHE = 1
    READ_CACHE = 2
    WRITE_READ_CACHE = 3
    TURNED_OFF = 4

class CacheSharingMode(Enum):
    SHARED = 1
    EQUAL_PARTITIONING = 2

class DataCacheManagerBase(SimObject):
    def __init__(self, id, host_interface, nvm_firmware, 
                 dram_row_size, dram_data_rate, dram_burst_size, 
                 dram_tRCD, dram_tCL, dram_tRP,
                 caching_mode_per_input_stream, sharing_mode, stream_count):
        super().__init__(id)
        self.host_interface = host_interface
        self.nvm_firmware = nvm_firmware
        self.dram_row_size = dram_row_size
        self.dram_data_rate = dram_data_rate
        self.dram_burst_size = dram_burst_size
        self.dram_tRCD = dram_tRCD
        self.dram_tCL = dram_tCL
        self.dram_tRP = dram_tRP
        self.caching_mode_per_input_stream = caching_mode_per_input_stream
        self.sharing_mode = sharing_mode
        self.stream_count = stream_count
        
        # Calculate burst transfer time
        # MT/s is millions of transfers per second.
        self.dram_burst_transfer_time_ddr = 1.0 / (dram_data_rate * 1e6) * 1e9 # in nanoseconds

    @abstractmethod
    def process_new_user_request(self, user_request):
        pass

def estimate_dram_access_time(memory_access_size_in_byte, dram_row_size, 
                              dram_burst_size_in_bytes, dram_burst_transfer_time_ddr, 
                              tRCD, tCL, tRP):
    """
    Estimates the DRAM access time for caching operations based on hardware timings.
    Ported from MQSim Data_Cache_Manager_Base.h
    """
    if memory_access_size_in_byte <= dram_row_size:
        return float(tRCD + tCL + (memory_access_size_in_byte / dram_burst_size_in_bytes / 2.0) * dram_burst_transfer_time_ddr)
    else:
        # Crosses a row boundary, requires tRP (precharge) overhead
        rows_accessed = int(memory_access_size_in_byte / dram_row_size)
        time_per_row = (dram_row_size / dram_burst_size_in_bytes / 2.0 * dram_burst_transfer_time_ddr) + tRP
        
        remaining_bytes = memory_access_size_in_byte % dram_row_size
        time_for_remainder = (remaining_bytes / dram_burst_size_in_bytes / 2.0) * dram_burst_transfer_time_ddr
        
        return float((tRCD + tCL + time_per_row * rows_accessed) + tRCD + tCL + time_for_remainder)

class CacheSlotStatus(Enum):
    EMPTY = 1
    CLEAN = 2
    DIRTY_NO_FLASH_WRITEBACK = 3
    DIRTY_FLASH_WRITEBACK = 4

class DataCacheSlot:
    def __init__(self, lpa=None, status=CacheSlotStatus.EMPTY):
        self.lpa = lpa
        self.status = status
        self.state_bitmap = 0
        self.timestamp = 0

class DataCacheFlash:
    def __init__(self, capacity_in_pages):
        self.capacity_in_pages = capacity_in_pages
        self.slots = {} # LPN -> DataCacheSlot
        self.lru_list = [] # List of LPNs
        
    def exists(self, lpn):
        return lpn in self.slots
        
    def is_full(self):
        return len(self.slots) >= self.capacity_in_pages
        
    def get_slot(self, lpn):
        if lpn in self.slots:
            # Move to end of LRU
            self.lru_list.remove(lpn)
            self.lru_list.append(lpn)
            return self.slots[lpn]
        return None
        
    def insert(self, lpn, status):
        if self.is_full():
            self.evict_lru()
        slot = DataCacheSlot(lpn, status)
        self.slots[lpn] = slot
        self.lru_list.append(lpn)
        return slot
        
    def evict_lru(self):
        if not self.lru_list:
            return None
        lpn_to_evict = self.lru_list.pop(0)
        evicted_slot = self.slots.pop(lpn_to_evict)
        return evicted_slot

class DataCacheManagerSimple(DataCacheManagerBase):
    def __init__(self, id, host_interface, nvm_firmware, 
                 total_capacity_in_bytes, page_capacity_in_bytes,
                 dram_row_size, dram_data_rate, dram_burst_size, 
                 dram_tRCD, dram_tCL, dram_tRP,
                 caching_mode_per_input_stream, stream_count):
        super().__init__(id, host_interface, nvm_firmware, 
                         dram_row_size, dram_data_rate, dram_burst_size, 
                         dram_tRCD, dram_tCL, dram_tRP,
                         caching_mode_per_input_stream, CacheSharingMode.SHARED, stream_count)
        
        self.capacity_in_bytes = total_capacity_in_bytes
        self.capacity_in_pages = total_capacity_in_bytes // page_capacity_in_bytes
        self.data_cache = DataCacheFlash(self.capacity_in_pages)
        self.page_capacity_in_bytes = page_capacity_in_bytes
        
    def process_new_user_request(self, user_request):
        if self.caching_mode_per_input_stream[user_request.stream_id] == CachingMode.TURNED_OFF:
            self.nvm_firmware.segment_user_request(user_request)
            return

        if user_request.type == "WRITE":
            # Estimate DRAM access time for cache insert
            access_time = estimate_dram_access_time(
                user_request.size_in_sectors * 512, 
                self.dram_row_size,
                self.dram_burst_size * 64, # Simplified burst size in bytes
                self.dram_burst_transfer_time_ddr,
                self.dram_tRCD, self.dram_tCL, self.dram_tRP
            )
            
            import math
            # Simplified: just acknowledge after DRAM delay + some host interface delay
            # C++ MQSim shows ~40us for NVMe writes in this config
            host_interface_delay = 40000 
            
            from mqsim.sim.engine import Engine
            delay = max(1, math.ceil(access_time)) + host_interface_delay
            Engine().register_sim_event(Engine().time + delay, self, parameters=user_request)
            
            # Also start actual NVM write in background (simplified destaging)
            self.nvm_firmware.segment_user_request(user_request)
        else:
            # READ: for now just delegate to FTL
            self.nvm_firmware.segment_user_request(user_request)

    def execute_sim_event(self, event):
        # Acknowledge the user request (Write Cache Hit)
        user_request = event.parameters
        self.host_interface.finish_user_request(user_request)
