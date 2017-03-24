import logging

from hvapi.clr_utils import InvocationException, Node, Relation, VirtualSystemSettingDataNode, Property, MOHTransformers, \
  VirtualSystemManagementService
from hvapi.hyperv_nonblocking import HypervHost, ComPort

FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

path = (
  VirtualSystemSettingDataNode,
  Node(Relation.RELATED, "Msvm_SyntheticEthernetPortSettingData"),
  Node(Relation.RELATED, "Msvm_EthernetPortAllocationSettingData"),
  Node(Relation.PROPERTY, "HostResource", (Property.ARRAY, MOHTransformers.from_reference))
)
hv_host = HypervHost()
settings = {
  "Msvm_MemorySettingData": {
    "DynamicMemoryEnabled": True,
    "Limit": 4096,
    "Reservation": 2048,
    "VirtualQuantity": 2048
  },
  "Msvm_ProcessorSettingData": {
    "VirtualQuantity": 8
  },
  "Msvm_VirtualSystemSettingData": {
    "VirtualNumaEnabled": False
  }
}
test1_vm = hv_host.create_machine("test1", settings)
# comport2 = hello_vm.get_com_port(ComPort.COM1)
# print(comport2.name)

pass