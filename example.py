import logging

from hvapi.hyperv import HypervHost

FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
host = HypervHost()
internal_switch = host.switches_by_name("internal")[0]
hello_machine = host.machines_by_name("hello")[0]
print(hello_machine.id)
print(hello_machine.is_connected_to_switch(internal_switch))
settings = {
  "Msvm_MemorySettingData": {
    "DynamicMemoryEnabled": True,
    "Limit": 4096,
    "Reservation": 2048,
    "VirtualQuantity": 2048
  },
  "Msvm_ProcessorSettingData": {
    "VirtualQuantity": 8
  }
}
hello_machine.apply_properties_group(settings)
# hello_machine.connect_to_switch(internal_switch)s

if __name__ == "__main__":
  pass
