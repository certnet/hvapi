import asyncio
import logging

import sys

from hvapi.hyperv import HypervHost

if sys.platform == 'win32':
  loop = asyncio.ProactorEventLoop()
  asyncio.set_event_loop(loop)

FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)


async def main_coro():
  host = HypervHost()
  internal_switch = (await host.switches_by_name("internal"))[0]
  hello_machine = (await host.machines_by_name("hello"))[0]
  print(hello_machine.id)
  print(await hello_machine.is_connected_to_switch(internal_switch))
  # settings = {
  #   "Msvm_MemorySettingData": {
  #     "DynamicMemoryEnabled": True,
  #     "Limit": 4096,
  #     "Reservation": 2048,
  #     "VirtualQuantity": 2048
  #   },
  #   "Msvm_ProcessorSettingData": {
  #     "VirtualQuantity": 8
  #   }
  # }
  # hello_machine.apply_properties_group(settings)

loop = asyncio.get_event_loop()
loop.run_until_complete(main_coro())
loop.close()


# hello_machine.connect_to_switch(internal_switch)s

if __name__ == "__main__":
  pass
