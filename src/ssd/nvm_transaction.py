class TransactionType:
    READ = "READ"
    WRITE = "WRITE"
    ERASE = "ERASE"

class TransactionSource:
    USERIO = "USERIO"
    CACHE = "CACHE"
    MAPPING = "MAPPING"
    GC_WL = "GC_WL"

class NVMTransaction:
    def __init__(self, stream_id, transaction_type, source, lpa, ppa=None, user_request=None):
        self.stream_id = stream_id
        self.type = transaction_type
        self.source = source
        self.lpa = lpa
        self.ppa = ppa
        self.user_request = user_request
        self.address = None # Physical address (channel, chip, die, plane, block, page)
        self.suspend_required = False
