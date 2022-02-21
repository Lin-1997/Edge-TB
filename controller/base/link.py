class Link (object):
	def __init__ (self, bw: int, unit: str):
		self.bw: int = bw
		self.unit: str = unit


class RealLink (Link):
	def __init__ (self, RID: int, bw: int, unit: str):
		super ().__init__ (bw, unit)
		self.RID: int = RID


class VirtualLink (Link):
	def __init__ (self, VID: int, bw: int, unit: str):
		super ().__init__ (bw, unit)
		self.VID: int = VID
