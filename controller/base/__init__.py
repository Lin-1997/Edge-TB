from typing import Type

from .manager import Manager
from .node import Testbed


def default_testbed (ip: str, dir_name: str, manager_class: Type [Manager],
		host_port: int = 8000) -> Testbed:
	"""
	Default settings suitable for most situations.

	:param ip: ip of the testbed controller.
	:param dir_name: yml file saved in $(dir_name) folder.
	:param manager_class: class of Manager.
	:param host_port: emulated node maps dml port to emulator's host port
	starting from $(host_port).
	"""
	return Testbed (ip, host_port, dir_name, manager_class)
