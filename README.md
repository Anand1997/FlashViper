# FlashViper: High-Fidelity Python Port of MQSim

FlashViper is a high-performance, high-fidelity SSD simulator ported from the original C++ MQSim. It is designed for researchers and engineers who prefer the flexibility of Python while requiring the accurate performance modeling of a hardware-validated simulator.

## Key Features

### 1. NVMe Front-end Modeling
- **Submission & Completion Queues (SQ/CQ)**: Full circular buffer logic.
- **Doorbell Registers**: Accurate simulation of host-to-SSD communication.
- **Weighted Round Robin (WRR)**: Prioritized command fetching across multiple streams (URGENT, HIGH, MEDIUM, LOW).
- **PCIe Link Modeling**: Bandwidth-aware transfer delays based on lane count and GB/s settings.

### 2. Advanced FTL & Address Mapping
- **Cached Mapping Table (CMT)**: Realistic modeling of mapping cache hits/misses with LRU eviction.
- **Multi-Stream Domains**: Support for independent or shared mapping domains.
- **Configurable Parallelism**: Support for multiple plane allocation schemes (CWDP, CDWP, WDCP, etc.).
- **Ideal vs. Realistic**: Toggle between zero-latency mapping and realistic flash-backed mapping traffic.

### 3. Garbage Collection & Backend Scheduling
- **Threshold-Driven GC**: Implements soft and hard free-block thresholds.
- **RGA Policy**: Randomized Greedy Algorithm for efficient victim block selection.
- **Urgent GC Prioritization**: Backend TSU automatically prioritizes GC over user I/O when free blocks are critical.
- **Transaction Suspend/Resume**: Support for Read-over-Write and Read-over-Erase to minimize latency.

### 4. NVM Backend & PHY
- **Detailed PHY Timing**: Modeling of ONFI bus contention and Command/Address/Data transfer overheads (tCAD).
- **MLC/TLC Latency**: Accurate page-level latency modeling (LSB, CSB, MSB) based on flash technology.

### 5. SSD Preconditioning
- **Distribution-Aware Aging**: Fast-forward SSD state to a target occupancy ratio using Uniform, Hot/Cold, or Streaming distributions before starting the main workload.

## Usage

### Prerequisites
- Python 3.8+
- `pytest` (for running tests)

### Running a Simulation
Run the simulator using the same XML configuration and workload files used by the original MQSim:

```powershell
$env:PYTHONPATH="."
python mqsim/main.py -i <path_to_ssdconfig.xml> -w <path_to_workload.xml>
```

### Analyzing Results
FlashViper generates results in the **exact same XML format** as the original MQSim. After a simulation, check for files named `<workload_name>_scenario_<id>.xml`. These files include:
- **Host Stats**: IOPS, Bandwidth, and Average Device Response Time.
- **FTL Stats**: Flash command counts (Read/Program/Erase) and CMT performance.
- **TSU Stats**: Queue occupancy and waiting times.

## Component Structure
- `mqsim/host`: Host-side logic (IO flows, PCIe Root Complex).
- `mqsim/ssd`: Internal SSD firmware logic (FTL, Data Cache, Host Interface, TSU).
- `mqsim/nvm_chip`: Low-level flash memory modeling.
- `mqsim/exec`: Execution and parameter management.
- `mqsim/utils`: Common utilities including the MQSim-standard XML results writer.

## Parity with MQSim C++
FlashViper has been verified against the original MQSim C++ implementation to ensure behavioral parity. It correctly models the performance impact of internal SSD management tasks, providing research-grade accuracy in a Python environment.
