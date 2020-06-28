class JSONable:
	def to_json (self):
		pass

	def from_json (self, json_str):
		pass


TYPE_SW = 1
TYPE_HOST = 2
TYPE_PH = 0

# min_quota需按实际docker host数量确定。具体算法是min_quota * max(optional_cpu_weights) * docker_host_num <= 1000000。
min_quota = 10000  # 10ms
# 随机生成图的重要配置，random_graph函数会根据以下四个列表，为四个关键属性分别从各个列表中随机选取一个值。
optional_random_bandwidths = [1, 10, 100, 1000]  # 单位：Mbps
optional_random_delays = ["0ms", "10ms", "100ms", "200ms"]
optional_cpu_weights = [1, 2, 3, 4]  # CPU分配的权重——影响docker host的CPU性能（权重越大，所分配到的CPU性能越高）
optional_mem_limits = ["1G", "2G", "4G"]
