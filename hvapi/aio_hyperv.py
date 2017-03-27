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
from asyncio import AbstractEventLoop
from concurrent.futures import Executor
from typing import List, Dict, Any

from hvapi.disk.vhd import VHDDisk
from hvapi.hyperv import HypervHost, VirtualMachine, VirtualComPort, VirtualNetworkAdapter, VirtualSwitch
from hvapi.types import VirtualMachineGeneration, VirtualMachineState, ComPort


class AioVirtualSwitch(object):
  def __init__(self, main_object: VirtualSwitch, executor: Executor, event_loop: AbstractEventLoop):
    self.main_object = main_object
    self.executor = executor
    self.event_loop = event_loop

  async def get_name(self):
    return await self.event_loop.run_in_executor(self.executor, lambda: self.main_object.name)

  async def get_id(self):
    return await self.event_loop.run_in_executor(self.executor, lambda: self.main_object.id)


class AioVirtualNetworkAdapter(object):
  def __init__(self, main_object: VirtualNetworkAdapter, executor: Executor, event_loop: AbstractEventLoop):
    self.main_object = main_object
    self.executor = executor
    self.event_loop = event_loop

  async def get_address(self) -> str:
    return await self.event_loop.run_in_executor(self.executor, lambda: self.main_object.address)

  async def get_switch(self) -> 'AioVirtualSwitch':
    return AioVirtualSwitch(await self.event_loop.run_in_executor(self.executor, lambda: self.main_object.switch), self.executor, self.event_loop)

  async def connect(self, virtual_switch: 'AioVirtualSwitch'):
    await self.event_loop.run_in_executor(self.executor, self.main_object.connect, virtual_switch.main_object)


class AioVirtualComPort(object):
  def __init__(self, main_object: VirtualComPort, executor: Executor, event_loop: AbstractEventLoop):
    self.main_object = main_object
    self.executor = executor
    self.event_loop = event_loop

  async def get_name(self) -> str:
    return await self.event_loop.run_in_executor(self.executor, lambda: self.main_object.name)

  async def get_path(self) -> str:
    return await self.event_loop.run_in_executor(self.executor, lambda: self.main_object.path)

  async def set_path(self, value):
    await self.event_loop.run_in_executor(self.executor, lambda: setattr(self.main_object, 'path', value))


class AioVirtualMachine(object):
  def __init__(self, main_object: VirtualMachine, executor: Executor, event_loop: AbstractEventLoop):
    self.main_object = main_object
    self.executor = executor
    self.event_loop = event_loop

  async def apply_properties(self, class_name: str, properties: Dict[str, Any]):
    await self.event_loop.run_in_executor(self.executor, self.main_object.apply_properties, class_name, properties)

  async def apply_properties_group(self, properties_group: Dict[str, Dict[str, Any]]):
    await self.event_loop.run_in_executor(self.executor, self.main_object.apply_properties_group, properties_group)

  async def get_name(self) -> str:
    return await self.event_loop.run_in_executor(self.executor, lambda: self.main_object.name)

  async def get_id(self) -> str:
    return await self.event_loop.run_in_executor(self.executor, lambda: self.main_object.id)

  async def get_state(self) -> VirtualMachineState:
    return await self.event_loop.run_in_executor(self.executor, lambda: self.main_object.state)

  async def start(self):
    await self.event_loop.run_in_executor(self.executor, self.main_object.start)

  async def stop(self, force=False, hard=False):
    await self.event_loop.run_in_executor(self.executor, self.main_object.stop, force, hard)

  async def kill(self):
    await self.event_loop.run_in_executor(self.executor, self.main_object.kill)

  async def save(self):
    await self.event_loop.run_in_executor(self.executor, self.main_object.save)

  async def pause(self):
    await self.event_loop.run_in_executor(self.executor, self.main_object.pause)

  async def add_adapter(self, static_mac=False, mac=None, adapter_name="Network Adapter") -> 'AioVirtualNetworkAdapter':
    return AioVirtualNetworkAdapter(await self.event_loop.run_in_executor(self.executor, self.main_object.add_adapter, static_mac, mac, adapter_name), self.executor, self.event_loop)

  async def is_connected_to_switch(self, virtual_switch: 'AioVirtualSwitch'):
    await self.event_loop.run_in_executor(self.executor, self.main_object.is_connected_to_switch, virtual_switch.main_object)

  async def add_vhd_disk(self, vhd_disk: VHDDisk):
    await self.event_loop.run_in_executor(self.executor, self.main_object.add_vhd_disk, vhd_disk)

  async def get_network_adapters(self) -> List[AioVirtualNetworkAdapter]:
    return [AioVirtualNetworkAdapter(va, self.executor, self.event_loop) for va in await self.event_loop.run_in_executor(self.executor, lambda: self.main_object.network_adapters)]

  async def get_com_ports(self) -> List[AioVirtualComPort]:
    return [AioVirtualComPort(com, self.executor, self.event_loop) for com in await self.event_loop.run_in_executor(self.executor, lambda: self.main_object.com_ports)]

  async def get_com_port(self, port: ComPort):
    return AioVirtualComPort(await self.event_loop.run_in_executor(self.executor, self.main_object.get_com_port, port), self.executor, self.event_loop)


class AioHypervHost(object):
  def __init__(self, main_object: HypervHost, executor: Executor, event_loop: AbstractEventLoop):
    self.main_object = main_object
    self.executor = executor
    self.event_loop = event_loop

  async def get_switches(self) -> List[AioVirtualSwitch]:
    return [AioVirtualSwitch(vs, self.executor, self.event_loop) for vs in await self.event_loop.run_in_executor(self.executor, lambda: self.main_object.switches)]

  async def switches_by_name(self, name) -> AioVirtualSwitch:
    return [AioVirtualSwitch(vs, self.executor, self.event_loop) for vs in await self.event_loop.run_in_executor(self.executor, self.main_object.switches_by_name, name)]

  async def switch_by_id(self, switch_id) -> AioVirtualSwitch:
    return AioVirtualSwitch(await self.event_loop.run_in_executor(self.executor, self.main_object.switch_by_id, switch_id), self.executor, self.event_loop)

  async def get_machines(self) -> List[AioVirtualMachine]:
    return [AioVirtualMachine(vs, self.executor, self.event_loop) for vs in await self.event_loop.run_in_executor(self.executor, lambda: self.main_object.machines)]

  async def machines_by_name(self, name) -> List[AioVirtualMachine]:
    return [AioVirtualMachine(vs, self.executor, self.event_loop) for vs in await self.event_loop.run_in_executor(self.executor, self.main_object.machines_by_name, name)]

  async def machine_by_id(self, machine_id) -> AioVirtualMachine:
    return AioVirtualMachine(await self.event_loop.run_in_executor(self.executor, self.main_object.machine_by_id, machine_id), self.executor, self.event_loop)

  async def create_machine(self, name, properties_group: Dict[str, Dict[str, Any]] = None, machine_generation: VirtualMachineGeneration = VirtualMachineGeneration.GEN1) -> AioVirtualMachine:
    return AioVirtualMachine(await self.event_loop.run_in_executor(self.executor, self.main_object.create_machine, name, properties_group, machine_generation), self.executor, self.event_loop)
