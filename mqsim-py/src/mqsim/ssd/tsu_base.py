from abc import ABC, abstractmethod

class TSUBase(ABC):
    def __init__(self):
        self.opened_scheduling_reqs = 0
        self.transaction_receive_slots = []
        self.transaction_dispatch_slots = []

    def prepare_for_transaction_submit(self):
        self.opened_scheduling_reqs += 1
        if self.opened_scheduling_reqs > 1:
            return
        self.transaction_receive_slots.clear()

    def submit_transaction(self, transaction):
        self.transaction_receive_slots.append(transaction)

    @abstractmethod
    def schedule(self):
        pass

    @abstractmethod
    def service_read_transaction(self, chip):
        pass

    @abstractmethod
    def service_write_transaction(self, chip):
        pass

    @abstractmethod
    def service_erase_transaction(self, chip):
        pass

    def _transaction_is_ready(self, transaction):
        if transaction.type == "READ":
            return True
        elif transaction.type == "WRITE":
            return getattr(transaction, 'related_read', None) is None
        elif transaction.type == "ERASE":
            return len(getattr(transaction, 'page_movement_activities', [])) == 0
        return True
