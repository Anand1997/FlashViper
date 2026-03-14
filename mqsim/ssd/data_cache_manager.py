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
    def __init__(self, capacity_in_pages, stream_count=1, sharing_mode=CacheSharingMode.SHARED):
        self.capacity_in_pages = capacity_in_pages
        self.stream_count = stream_count
        self.sharing_mode = sharing_mode
        
        if sharing_mode == CacheSharingMode.EQUAL_PARTITIONING:
            self.partition_capacity = capacity_in_pages // stream_count
            self.slots = [{} for _ in range(stream_count)] # LPN -> DataCacheSlot
            self.lru_list = [[] for _ in range(stream_count)]
        else:
            self.slots = [{}] # Index 0 is shared
            self.lru_list = [[]]
        
    def exists(self, lpn, stream_id=0):
        pool_idx = stream_id if self.sharing_mode == CacheSharingMode.EQUAL_PARTITIONING else 0
        return lpn in self.slots[pool_idx]
        
    def is_full(self, stream_id=0):
        pool_idx = stream_id if self.sharing_mode == CacheSharingMode.EQUAL_PARTITIONING else 0
        capacity = self.partition_capacity if self.sharing_mode == CacheSharingMode.EQUAL_PARTITIONING else self.capacity_in_pages
        return len(self.slots[pool_idx]) >= capacity
        
    def get_slot(self, lpn, stream_id=0):
        pool_idx = stream_id if self.sharing_mode == CacheSharingMode.EQUAL_PARTITIONING else 0
        if lpn in self.slots[pool_idx]:
            # Move to end of LRU
            self.lru_list[pool_idx].remove(lpn)
            self.lru_list[pool_idx].append(lpn)
            return self.slots[pool_idx][lpn]
        return None
        
    def insert(self, lpn, status, stream_id=0):
        pool_idx = stream_id if self.sharing_mode == CacheSharingMode.EQUAL_PARTITIONING else 0
        if self.is_full(stream_id):
            self.evict_lru(stream_id)
        slot = DataCacheSlot(lpn, status)
        self.slots[pool_idx][lpn] = slot
        self.lru_list[pool_idx].append(lpn)
        return slot
        
    def evict_lru(self, stream_id=0):
        pool_idx = stream_id if self.sharing_mode == CacheSharingMode.EQUAL_PARTITIONING else 0
        if not self.lru_list[pool_idx]:
            return None
        lpn_to_evict = self.lru_list[pool_idx].pop(0)
        evicted_slot = self.slots[pool_idx].pop(lpn_to_evict)
        return evicted_slot

class DataCacheManagerSimple(DataCacheManagerBase):
    def __init__(self, id, host_interface, nvm_firmware, 
                 total_capacity_in_bytes, page_capacity_in_bytes,
                 dram_row_size, dram_data_rate, dram_burst_size, 
                 dram_tRCD, dram_tCL, dram_tRP,
                 caching_mode_per_input_stream, stream_count, sharing_mode=CacheSharingMode.SHARED):
        super().__init__(id, host_interface, nvm_firmware, 
                         dram_row_size, dram_data_rate, dram_burst_size, 
                         dram_tRCD, dram_tCL, dram_tRP,
                         caching_mode_per_input_stream, sharing_mode, stream_count)
        
        self.capacity_in_bytes = total_capacity_in_bytes
        self.capacity_in_pages = total_capacity_in_bytes // page_capacity_in_bytes
        self.data_cache = DataCacheFlash(self.capacity_in_pages, stream_count, sharing_mode)
        self.page_capacity_in_bytes = page_capacity_in_bytes
        
    def process_new_user_request(self, user_request):
        if self.caching_mode_per_input_stream[user_request.stream_id] == CachingMode.TURNED_OFF:
            # Delay FTL call slightly to avoid instant feedback loop in same sim time
            from mqsim.sim.engine import Engine
            Engine().register_sim_event(Engine().time + 1, self.nvm_firmware, parameters=user_request, type="SEGMENT")
            return

        from mqsim.sim.engine import Engine
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
            host_interface_delay = 40000 
            
            delay = max(1, math.ceil(access_time)) + host_interface_delay
            # Acknowledge user request after delay
            Engine().register_sim_event(Engine().time + delay, self, parameters=user_request)
            
            # Start actual NVM write after a small delay to avoid recursion
            Engine().register_sim_event(Engine().time + 1, self.nvm_firmware, parameters=user_request, type="SEGMENT")
        else:
            # READ: for now just delegate to FTL with small delay
            Engine().register_sim_event(Engine().time + 1, self.nvm_firmware, parameters=user_request, type="SEGMENT")

    def execute_sim_event(self, event):
        # Acknowledge the user request (Write Cache Hit)
        user_request = event.parameters
        self.host_interface.finish_user_request(user_request)
