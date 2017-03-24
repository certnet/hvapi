# import logging
#
# from hvapi.clr_utils import InvocationException, Node, Relation, VirtualSystemSettingDataNode, Property, MOHTransformers
# from hvapi.hyperv_nonblocking import HypervHost
#
# FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
# logging.basicConfig(format=FORMAT, level=logging.DEBUG)
#
# path = (
#   VirtualSystemSettingDataNode,
#   Node(Relation.RELATED, "Msvm_SyntheticEthernetPortSettingData"),
#   Node(Relation.RELATED, "Msvm_EthernetPortAllocationSettingData"),
#   Node(Relation.PROPERTY, "HostResource", (Property.ARRAY, MOHTransformers.from_reference))
# )
# hv_host = HypervHost()
# hello_vm = hv_host.machines_by_name("hello")[-1]
# hello_vm.connect_to_switch("hello")
# res = hello_vm.traverse(path)
# # res = hello_vm.traverse(path)
# # try:
# #   hello_vm.start()
# # except InvocationException:
# #   raise
# # hello_vm.stop()
# # hello_vm.pause()
# # hello_vm.start()
# print(hello_vm.state)

class Mac(object):
  def __init__(self):
    self.b1 = 0
    self.b2 = 0
    self.b3 = 0
    sel