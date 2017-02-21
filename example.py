import logging

from hvapi.hyperv import HypervHost, VirtualMachine, VirtualMachineGeneration, VHDDisk

FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
host = HypervHost()
internal_switch = host.switch_by_name("internal")
hello_machine = host.machine_by_name("hello")
print(hello_machine.is_connected_to_switch(internal_switch))
# hello_machine.connect_to_switch(internal_switch)

if __name__ == "__main__":
  pass