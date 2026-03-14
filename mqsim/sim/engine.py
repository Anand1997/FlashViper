import heapq

class SimEvent:
    def __init__(self, fire_time, target_object, parameters=None, type=0):
        self.fire_time = fire_time
        self.target_object = target_object
        self.parameters = parameters
        self.type = type
        self.ignore = False

    def __lt__(self, other):
        return self.fire_time < other.fire_time

class Engine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Engine, cls).__new__(cls)
            cls._instance._reset()
        return cls._instance

    def _reset(self):
        self._sim_time = 0
        self._event_list = []
        self._started = False
        self._stop = False
        self._objects = {}

    @property
    def time(self):
        return self._sim_time

    def add_object(self, obj):
        self._objects[obj.id] = obj

    def get_object(self, obj_id):
        return self._objects.get(obj_id)

    def register_sim_event(self, fire_time, target_object, parameters=None, type=0):
        event = SimEvent(fire_time, target_object, parameters, type)
        heapq.heappush(self._event_list, event)
        return event

    def ignore_sim_event(self, event):
        if event:
            event.ignore = True

    def start_simulation(self):
        self._started = True
        
        # 1. Validate config
        for obj in self._objects.values():
            obj.validate_simulation_config()
            
        # 2. Setup triggers
        for obj in self._objects.values():
            obj.setup_triggers()
            
        # 3. Start simulation for all objects
        for obj in self._objects.values():
            obj.start_simulation()

        # 4. Main event loop
        while self._event_list and not self._stop:
            event = heapq.heappop(self._event_list)
            if event.ignore:
                continue
            
            self._sim_time = event.fire_time
            event.target_object.execute_sim_event(event)
        self._started = False

    def stop_simulation(self):
        self._stop = True

    def reset(self):
        self._reset()
