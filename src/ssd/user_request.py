class UserRequest:
    def __init__(self, stream_id, type, lsa, size_in_sectors):
        self.stream_id = stream_id
        self.type = type
        self.lsa = lsa
        self.size_in_sectors = size_in_sectors
        self.transaction_list = []
        self.sectors_serviced_from_cache = 0
        self.already_finished = False
        
    @property
    def is_finished(self):
        return len(self.transaction_list) == 0 and self.sectors_serviced_from_cache == 0
