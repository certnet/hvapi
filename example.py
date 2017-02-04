import pprint

from hvapi.wmi_utils import WmiHelper, Node, Path, Property, management_object_traversal, get_wmi_object_properties

helper = WmiHelper()
linux_vm = helper.query_one(
  'SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine" AND ElementName = "linux"')

port_to_switch_path = (
  Node(Path.RELATED, "Msvm_VirtualSystemSettingData"),
  Node(Path.RELATED, "Msvm_SyntheticEthernetPortSettingData"),
  Node(Path.RELATED, "Msvm_EthernetPortAllocationSettingData"),
  Node(Path.PROPERTY, "HostResource", (Property.ARRAY, helper.get))
)
result = management_object_traversal(port_to_switch_path, linux_vm)
pprint.pprint(result)

subtype_path = (
  Node(Path.RELATED, "Msvm_VirtualSystemSettingData"),
  Node(Path.PROPERTY, "VirtualsystemSubtype", (Property.SINGLE,))
)
sub_type = management_object_traversal(subtype_path, linux_vm)

pprint.pprint(get_wmi_object_properties(result[-1][-1]))
pprint.pprint(get_wmi_object_properties(result[-2][-1]))
pass
