from mqsim.ssd.flash_block_manager import FlashBlockManager
from mqsim.ssd.mapping_unit import PageLevelAddressMapping
from mqsim.ssd.tsu_outoforder import TSUOutOfOrder
from mqsim.ssd.nvm_transaction import NVMTransaction, TransactionType, TransactionSource
from mqsim.utils.random_generator import RandomGenerator

class FTL:
    def __init__(self, channel_no, chip_no_per_channel, die_no_per_chip, 
                 plane_no_per_die, block_no_per_plane, page_no_per_block, 
                 page_size_in_sectors, over_provisioning_ratio, seed):
        
        self.channel_no = channel_no
        self.chip_no_per_channel = chip_no_per_channel
        self.die_no_per_chip = die_no_per_chip
        self.plane_no_per_die = plane_no_per_die
        self.block_no_per_plane = block_no_per_plane
        self.page_no_per_block = page_no_per_block
        self.page_size_in_sectors = page_size_in_sectors
        self.over_provisioning_ratio = over_provisioning_ratio
        
        self.random_generator = RandomGenerator(seed)

        # 1. Initialize Block Manager
        self.block_manager = FlashBlockManager(
            channel_no, chip_no_per_channel, die_no_per_chip, 
            plane_no_per_die, block_no_per_plane, page_no_per_block
        )

        # 2. Initialize Mapping Unit
        total_physical_pages = (channel_no * chip_no_per_channel * 
                                die_no_per_chip * plane_no_per_die * 
                                block_no_per_plane * page_no_per_block)
        
        no_of_logical_pages = int(total_physical_pages * (1.0 - over_provisioning_ratio))
        self.address_mapping_unit = PageLevelAddressMapping(no_of_logical_pages)

        # 3. Initialize Transaction Scheduling Unit (TSU)
        self.tsu = TSUOutOfOrder("FTL.TSU", channel_no, chip_no_per_channel)

    def segment_user_request(self, user_request):
        """
        Breaks a host-level request into page-sized NVM transactions.
        """
        lsa = user_request.lsa
        size = user_request.size_in_sectors
        
        transactions = []
        
        # Calculate the starting LPA and offset
        current_lsa = lsa
        remaining_size = size
        
        while remaining_size > 0:
            lpa = current_lsa // self.page_size_in_sectors
            # In MQSim, multiple sectors can be in one transaction if they fit in one page
            # For simplicity, we create one transaction per page boundary
            sectors_in_this_page = min(remaining_size, 
                                       self.page_size_in_sectors - (current_lsa % self.page_size_in_sectors))
            
            tr = NVMTransaction(
                stream_id=user_request.stream_id,
                transaction_type=user_request.type,
                source=TransactionSource.USERIO,
                lpa=lpa,
                user_request=user_request
            )
            transactions.append(tr)
            user_request.transaction_list.append(tr)
            
            current_lsa += sectors_in_this_page
            remaining_size -= sectors_in_this_page
            
        return transactions
