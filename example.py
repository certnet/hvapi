import logging

from hvapi.hyperv import HypervHost, VirtualMachine, VirtualMachineGeneration, VHDDisk

FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
host = HypervHost()
machine = host.machine_by_name("linux")
print(host.machine_by_name("linux").state)
print(host.machine_by_name("hello").state)


if __name__ == "__main__":
  pass