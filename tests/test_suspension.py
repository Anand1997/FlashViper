import pytest
from mqsim.sim.engine import Engine
from mqsim.nvm_chip.flash_chip import FlashChip, ChipStatus, DieStatus
from mqsim.ssd.tsu_outoforder import TSUOutOfOrder
from mqsim.ssd.nvm_transaction import NVMTransaction, TransactionType, TransactionSource

def test_flash_command_suspension():
    engine = Engine()
    engine.reset()
    
    # Setup TSU and Chip
    tsu = TSUOutOfOrder("TSU0", 1, 1)
    # Program: 5000ns, Read: 1000ns
    chip = FlashChip(
        "Chip0", 0, 0, "SLC", 1, 1,
        read_latencies=[1000], program_latencies=[5000], erase_latency=10000,
        suspend_program_latency=100, suspend_erase_latency=100
    )
    engine.add_object(chip)
    tsu.phy = type('obj', (object,), {'get_chip': lambda c, i: chip})
    chip.on_idle.connect(tsu.handle_chip_idle_signal)

    # 1. Submit a slow PROGRAM transaction
    tx_prog = NVMTransaction(0, "WRITE", TransactionSource.USERIO, 0)
    tx_prog.address = {"channel": 0, "chip": 0, "die": 0, "plane": 0, "page": 0}
    
    tsu.prepare_for_transaction_submit()
    tsu.submit_transaction(tx_prog)
    tsu.schedule()
    
    assert chip.dies[0].status == DieStatus.BUSY
    assert engine.time == 0
    
    # 2. At t=2000, submit an URGENT READ transaction
    # We simulate this by advancing engine slightly and then calling schedule
    engine.register_sim_event(2000, type('obj', (object,), {
        'id': 'trigger',
        'execute_sim_event': lambda ev: trigger_read()
    }))

    def trigger_read():
        tx_read = NVMTransaction(0, "READ", TransactionSource.USERIO, 1)
        tx_read.address = {"channel": 0, "chip": 0, "die": 0, "plane": 0, "page": 1}
        tsu.prepare_for_transaction_submit()
        tsu.submit_transaction(tx_read)
        tsu.schedule() # This should trigger suspension because Die is BUSY with WRITE

    engine.start_simulation()
    
    # Timing analysis:
    # t=0: Program starts (Expected finish t=5000)
    # t=2000: Read arrives. TSU sees busy die, calls chip.suspend(0).
    #        Die becomes IDLE. Read is issued immediately.
    #        Remaining Program time = 5000 - 2000 = 3000.
    # t=3000: Read finishes (2000 + 1000). 
    #        Die becomes IDLE. handle_chip_idle_signal calls service_chip_requests.
    #        service_chip_requests sees suspended transaction and resumes it.
    #        Program resumes with 3000ns remaining.
    # t=6000: Program finally finishes (3000 + 3000).
    
    assert engine.time == 6000
    assert chip.dies[0].status == DieStatus.IDLE
