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
        rows_accessed = memory_access_size_in_byte / dram_row_size / 2.0
        time_per_row = (dram_row_size / dram_burst_size_in_bytes / 2.0 * dram_burst_transfer_time_ddr) + tRP
        
        remaining_bytes = memory_access_size_in_byte % dram_row_size
        time_for_remainder = (remaining_bytes / dram_burst_size_in_bytes / 2.0) * dram_burst_transfer_time_ddr
        
        return float((tRCD + tCL + time_per_row * rows_accessed) + tRCD + tCL + time_for_remainder)
