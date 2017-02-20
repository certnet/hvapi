import logging

from hvapi.hyperv import HypervHost, VirtualMachine, VirtualMachineGeneration

FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
host = HypervHost()
machine = host.machine_by_name("linux")
print(host.machine_by_name("linux").state)
print(host.machine_by_name("hello").state)
# Msvm_MemorySettingData = {
#   "Limit": 4096,
#   "Reservation": 1024,
#   "DynamicMemoryEnabled": True
# }
# machine.apply_properties("Msvm_MemorySettingData", Msvm_MemorySettingData)
res = machine.network_adapters
res = machine.network_adapters
res = host.machine_by_name("test1")
res = host.machine_by_name("test1")
res = host.create_machine("test3")
res = host.machine_by_name("test1")
pass
pass
# print(machine.vcpu)
# machine.vcpu = 4
# print(machine.vcpu)
# machine.dynamic_memory = True
# print(machine.dynamic_memory)
# machine.start()
# print(machine.state)
# machine.stop()
# print(machine.state)
# # prev_state = None
# # while True:
# #   state = machine.state
# #   if state != prev_state:
# #     print(state)
# #   prev_state = state
# # pprint.pprint()
# # res.stop()
# # print(res)
pass

if __name__ == "__main__":
  pass