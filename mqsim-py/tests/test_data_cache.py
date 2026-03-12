import pytest
from mqsim.ssd.data_cache_manager import estimate_dram_access_time

def test_estimate_dram_access_time_small_access():
    # Access size fits within a single DRAM row
    memory_access_size = 4096  # 4KB
    dram_row_size = 8192      # 8KB
    dram_burst_size = 4       # 4 Bytes per burst
    dram_burst_transfer_time_ddr = 2.0 # ns
    tRCD = 13.0 # ns
    tCL = 13.0  # ns
    tRP = 13.0  # ns
    
    # Expected formula (from C++): tRCD + tCL + (access_size / burst_size / 2) * transfer_time
    # 13 + 13 + (4096 / 4 / 2) * 2.0 = 26 + (512) * 2.0 = 1050 ns
    time = estimate_dram_access_time(
        memory_access_size, dram_row_size, dram_burst_size,
        dram_burst_transfer_time_ddr, tRCD, tCL, tRP
    )
    
    assert time == 1050.0

def test_estimate_dram_access_time_large_access():
    # Access size spans multiple DRAM rows
    memory_access_size = 16384 # 16KB (2 rows)
    dram_row_size = 8192      # 8KB
    dram_burst_size = 4       # 4 Bytes per burst
    dram_burst_transfer_time_ddr = 2.0 # ns
    tRCD = 13.0 # ns
    tCL = 13.0  # ns
    tRP = 13.0  # ns
    
    time = estimate_dram_access_time(
        memory_access_size, dram_row_size, dram_burst_size,
        dram_burst_transfer_time_ddr, tRCD, tCL, tRP
    )
    
    # Should be greater than simply scaling up due to row precharge (tRP) overhead
    assert time > 2100.0 
