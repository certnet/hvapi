import logging

from hvapi.hyperv import HypervHost, VirtualMachine

FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
host = HypervHost()
res = HypervHost()
machine = host.machine_by_name("hello")
print(machine.vcpu)
machine.vcpu = 6
print(machine.vcpu)
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