class Nfs (object):
	def __init__ (self, tag: str, path: str, ip: str, mask: int):
		self.tag: str = tag
		self.path: str = path
		self.subnet: str = ip + '/' + str (mask)
