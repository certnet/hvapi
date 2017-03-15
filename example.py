"""
The MIT License

Copyright (c) 2017 Eugene Chekanskiy, echekanskiy@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
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
  switch = (await host.switches_by_name("internal"))[0]
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
      "VirtualNumaEnabled ": False
    }
  }
  machine = (await host.machines_by_name("test_machine"))[0]
  adapter = await machine.connect_to_switch(switch, static_mac="00:11:22:33:44:55")
  print(await adapter.address)
  # hello_machine = (await host.machines_by_name("centos6.8"))[0]
  # print(await hello_machine.state)

  # await hello_machine.apply_properties_group(settings)

loop = asyncio.get_event_loop()
loop.run_until_complete(main_coro())
loop.close()


# hello_machine.connect_to_switch(internal_switch)s

if __name__ == "__main__":
  pass
