class PageLevelAddressMapping:
    def __init__(self, no_of_logical_pages):
        self.no_of_logical_pages = no_of_logical_pages
        # Global Mapping Table: LPA -> PPA
        # In MQSim this is often an array, but dict is better for Python sparse handling
        self.gmt = {} 

    def get_ppa(self, stream_id, lpa):
        # In MQSim, each stream can have its own domain, 
        # but for now we implement a shared global table
        return self.gmt.get(lpa, -1)

    def update_mapping_info(self, stream_id, lpa, ppa):
        if lpa >= self.no_of_logical_pages:
            raise ValueError(f"LPA {lpa} exceeds logical capacity {self.no_of_logical_pages}")
        self.gmt[lpa] = ppa
