from mqsim.utils.random_generator import RandomGenerator

class SyntheticIOFlow:
    def __init__(self, read_ratio, start_lsa, end_lsa, seed):
        self.read_ratio = read_ratio
        self.start_lsa = start_lsa
        self.end_lsa = end_lsa
        self.rng = RandomGenerator(seed)

    def generate_next_request(self):
        # Determine request type
        prob = self.rng.float_random()
        req_type = "READ" if prob < self.read_ratio else "WRITE"
        
        # Determine LSA (Uniform)
        lsa = self.rng.uniform_uint(self.start_lsa, self.end_lsa)
        
        return {
            'type': req_type,
            'lsa': lsa,
            'size': 8 # Fixed size for now (matching workload.xml default)
        }
