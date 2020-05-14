class JSONable:
    def to_json(self):
        pass

    def from_json(self, json_str):
        pass


TYPE_SW = 1
TYPE_HOST = 2
TYPE_PH = 0

optional_random_bandwidths = [1, 10, 100, 1000]
optional_random_delays = ["0ms", "10ms", "100ms", "200ms"]
optional_cpu_quotas = [1, 2, 3, 4]
optional_mem_limits = ["1G", "2G", "4G"]
