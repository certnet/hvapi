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
import time
from enum import Enum
from typing import List, Dict, Any

from hvapi.types import ComputerSystem_RequestStateChange_ReturnCodes, ComputerSystem_EnabledState, ShutdownComponent_OperationalStatus, \
  ShutdownComponent_ShutdownComponent_ReturnCodes
from hvapi.clr_types import ComputerSystem_RequestStateChange_RequestedState, \
  ComputerSystem_RequestStateChange_ReturnCodes, ComputerSystem_EnabledState, ShutdownComponent_OperationalStatus, \
  ShutdownComponent_ShutdownComponent_ReturnCodes
from hvapi.powershell_utils import parse_properties, exec_powershell_checked, parse_select_object_output
from hvapi.clr_utils import ScopeHolder, ManagementObjectHolder, InvocationException, Node, Relation, \
  VirtualSystemSettingDataNode, Property, MOHTransformers, PropertySelector

# region PRIVATE
# ps scripts
# host scripts
_HOST_ALL_SWITCHES_CMD = """foreach ($switch in Get-VMSwitch) {
$switch | Select-Object -Property *
Write-Host --------------------
}"""
_HOST_SWITCH_BY_ID_CMD = """$switches = Get-VMSwitch -Id "{ID}"
foreach ($switch in $switches) {{
$switch | Select-Object -Property *
Write-Host --------------------
}}"""
_HOST_SWITCH_BY_NAME_CMD = """$switches = Get-VMSwitch -Name "{NAME}"
foreach ($switch in $switches) {{
$switch | Select-Object -Property *
Write-Host --------------------
}}"""
_HOST_ALL_MACHINES_CMD = """foreach ($vm in Get-VM) {
$vm | Select-Object -Property *
Write-Host --------------------
}"""
_HOST_MACHINE_BY_ID_CMD = """$vms = Get-VM -Id "{ID}"
foreach ($vm in $vms) {{
$vm | Select-Object -Property *
Write-Host --------------------
}}"""
_HOST_MACHINE_BY_NAME_CMD = """$vms = Get-VM -Name "{NAME}"
foreach ($vm in $vms) {{
$vm | Select-Object -Property *
Write-Host --------------------
}}"""
_HOST_MACHINE_CREATE_CMD = """
New-VM -Name {NAME} -Generation {GENERATION} | Select-Object -Property *
"""
# adapter scripts
_ADAPTER_GET_CONCRETE_ADAPTER_CMD = """$adapters = Get-VMNetworkAdapter -VM (Get-Vm -Id {VM_ID})
$adapters | Where-Object -Property Id -eq {ADAPTER_ID} | Select-Object -Property *
"""
# comport scripts
_ADAPTER_GET_CONCRETE_COMPORT_CMD = """$comports = Get-VMComPort -VM (Get-Vm -Id {VM_ID})
$comports | Where-Object -Property Id -eq {COMPORT_ID} | Select-Object -Property *
"""
# machine scripts
_MACHINE_GET_MACHINE_ADAPTERS_CMD = """$adapters = Get-VMNetworkAdapter -VM (Get-Vm -Id "{VM_ID}")
foreach ($adapter in $adapters) {{
$adapter | Select-Object -Property *
Write-Host --------------------
}}"""
_MACHINE_GET_MACHINE_COMPORTS_CMD = """$comports = Get-VMComPort -VM (Get-Vm -Id "{VM_ID}")
foreach ($comport in $comports) {{
$comport | Select-Object -Property *
Write-Host --------------------
}}"""
_MACHINE_CONNECT_TO_SWITCH_CMD = 'Add-VMNetworkAdapter -VM (Get-Vm -Id {ID}) -SwitchName "{SWITCH_NAME}"'
_MACHINE_CONNECT_TO_SWITCH_STATIC_MAC_CMD = 'Add-VMNetworkAdapter -VM (Get-Vm -Id {ID}) -SwitchName "{SWITCH_NAME}" -StaticMacAddress "{STATIC_MAC}"'
_MACHINE_ADD_VHD_CMD = 'Add-VMHardDiskDrive -VM (Get-Vm -Id {ID}) -Path "{VHD_PATH}"'
_MACHINE_GET_PROPERTY_CMD = '(Get-Vm -Id {ID}).{PROPERTY}'
_MACHINE_STOP_FORCE_CMD = 'Stop-VM -VM (Get-Vm -Id {ID}) -Force'
_MACHINE_STOP_TURNOFF_CMD = 'Stop-VM -VM (Get-Vm -Id {ID}) -TurnOff -Force'
_MACHINE_START_CMD = 'Start-VM -VM (Get-Vm -Id {ID})'
_MACHINE_SAVE_CMD = 'Save-VM -VM (Get-Vm -Id {ID})'
_MACHINE_PAUSE_CMD = 'Suspend-VM -VM (Get-Vm -Id {ID})'
_MACHINE_ADD_COMPORT_CMD = 'Set-VMComPort -VM (Get-Vm -Id {ID}) -Number {NUMBER} -Path {PATH}'
_MACHINE_KILL_MACHINE = "Stop-Process (Get-WmiObject Win32_Process | ? {{$_.Name -match 'vmwp' -and $_.CommandLine " \
                        "-match (Get-Vm -Id {ID}).Id.Guid}}).ProcessId -Force"
# WMI scripts
_Msvm_MemorySettingData_HEADER = """
$Msvm_VirtualSystemManagementService = Get-WmiObject -Namespace root\\virtualization\\v2 -Class Msvm_VirtualSystemManagementService
$Msvm_ComputerSystem = Get-WmiObject -Namespace root\\virtualization\\v2 -Class Msvm_ComputerSystem -Filter "Name='{VM_ID}'"
$Msvm_VirtualSystemSettingData = ($Msvm_ComputerSystem.GetRelated("Msvm_VirtualSystemSettingData", "Msvm_SettingsDefineState", $null, $null, "SettingData", "ManagedElement", $false, $null) | % {{$_}})
$TargetObject = $Msvm_VirtualSystemSettingData.getRelated("Msvm_MemorySettingData") | select -first 1

"""
_COMMON_FOOTER = """
$result = $Msvm_VirtualSystemManagementService.ModifyResourceSettings($TargetObject.GetText(2))
"""
_Msvm_ProcessorSettingData_HEADER = """
$Msvm_VirtualSystemManagementService = Get-WmiObject -Namespace root\\virtualization\\v2 -Class Msvm_VirtualSystemManagementService
$Msvm_ComputerSystem = Get-WmiObject -Namespace root\\virtualization\\v2 -Class Msvm_ComputerSystem -Filter "Name='{VM_ID}'"
$Msvm_VirtualSystemSettingData = ($Msvm_ComputerSystem.GetRelated("Msvm_VirtualSystemSettingData", "Msvm_SettingsDefineState", $null, $null, "SettingData", "ManagedElement", $false, $null) | % {{$_}})
$TargetObject = $Msvm_VirtualSystemSettingData.getRelated("Msvm_ProcessorSettingData") | select -first 1

"""
_Msvm_VirtualSystemSettingData_HEADER = """
$Msvm_VirtualSystemManagementService = Get-WmiObject -Namespace root\\virtualization\\v2 -Class Msvm_VirtualSystemManagementService
$Msvm_ComputerSystem = Get-WmiObject -Namespace root\\virtualization\\v2 -Class Msvm_ComputerSystem -Filter "Name='{VM_ID}'"
$TargetObject = ($Msvm_ComputerSystem.GetRelated("Msvm_VirtualSystemSettingData", "Msvm_SettingsDefineState", $null, $null, "SettingData", "ManagedElement", $false, $null) | % {{$_}})

"""
_Msvm_VirtualSystemSettingData_FOOTER = """
$result = $Msvm_VirtualSystemManagementService.ModifySystemSettings($TargetObject.GetText(2))
"""

_JOB_HANDLER_FOOTER = """
if($result.ReturnValue -eq 0){
  $host.SetShouldExit(0)
} ElseIf ($result.ReturnValue -ne 4096) {
  Write-Host "Operation failed:" $result
  $host.SetShouldExit(1)
} Else {
  $job=[WMI]$result.Job
  while ($job.JobState -eq 3 -or $job.JobState -eq 4) {
    start-sleep 1
  }
  if ($job.JobState -eq 7) {
    $host.SetShouldExit(0)
  } Else {
    Write-Host "ERRORCODE:" $job.ErrorCode
    Write-Host "ERRORMESSAGE:" $job.ErrorDescription
    $host.SetShouldExit(1)
  }
}
"""


def _generate_wmi_properties_setters(properties: dict):
  def transform_value(val):
    if isinstance(val, bool):
      if val:
        return "$true"
      else:
        return "$false"
    if isinstance(val, str):
      return '"%s"' % val
    return val

  result = ""
  for name, value in properties.items():
    result += "$TargetObject.%s = %s\n" % (name, transform_value(value))
  return result


_CLS_MAP = {
  "Msvm_MemorySettingData": (_Msvm_MemorySettingData_HEADER, _COMMON_FOOTER),
  "Msvm_ProcessorSettingData": (_Msvm_ProcessorSettingData_HEADER, _COMMON_FOOTER),
  "Msvm_VirtualSystemSettingData": (_Msvm_VirtualSystemSettingData_HEADER, _Msvm_VirtualSystemSettingData_FOOTER)
}
_CLS_MAP_PRIORITY = {
  "Msvm_VirtualSystemSettingData": 0
}


# endregion

class VirtualMachineGeneration(str, Enum):
  GEN1 = "1"
  GEN2 = "2"


class VirtualMachineState(int, Enum):
  UNDEFINED = -1
  RUNNING = 0
  STOPPED = 1
  SAVED = 2
  PAUSED = 3
  ERROR = 4


class VHDDisk(object):
  """
  Represents a VHD disk.
  """
  INFO = 'Get-VHD -Path "%s"'
  CLONE = 'New-VHD -Path "{PATH}" -ParentPath "{PARENT}" -Differencing'

  def __init__(self, vhd_file_path):
    self.vhd_file_path = vhd_file_path

  async def clone(self, path) -> 'VHDDisk':
    """
    Creates a differencing clone of VHD disk in ``path``.

    :param path: path to save clone of VHD disk
    """
    await exec_powershell_checked(self.CLONE.format(
      PATH=path,
      PARENT=self.vhd_file_path
    ))
    return VHDDisk(path)

  @property
  async def properties(self) -> Dict[str, str]:
    """
    Returns properties of VHD disk.

    :return: dictionary with properties
    """
    out = await exec_powershell_checked(self.INFO % self.vhd_file_path)
    return parse_properties(out)


class VirtualSwitch(ManagementObjectHolder):
  @property
  def name(self):
    return self.properties['ElementName']

  @property
  def id(self):
    return self.properties['Name']

  def __eq__(self, other):
    return self.id == other.id and self.name == other.name

  @classmethod
  def from_moh(cls, moh: ManagementObjectHolder) -> 'VirtualSwitch':
    return cls._create_cls_from_moh(cls, 'Msvm_VirtualEthernetSwitch', moh)


class VirtualMachineNetworkAdapter(ManagementObjectHolder):
  @property
  def address(self) -> str:
    return self.properties['Address']

  @property
  def switch(self) -> 'VirtualSwitch':
    result = []
    port_to_switch_path = (
      Node(Relation.RELATED, "Msvm_EthernetPortAllocationSettingData"),
      Node(Relation.PROPERTY, "HostResource", (Property.ARRAY, MOHTransformers.from_reference))
    )
    for _, virtual_switch in self.traverse(port_to_switch_path):
      result.append(VirtualSwitch.from_moh(virtual_switch))
    if len(result) > 1:
      raise Exception("Something horrible happened, virtual network adapter connected to more that one virtual switch")
    if result:
      return result[0]

  @classmethod
  def from_moh(cls, moh: ManagementObjectHolder) -> 'VirtualMachineNetworkAdapter':
    return cls._create_cls_from_moh(cls, 'Msvm_SyntheticEthernetPortSettingData', moh)


class VirtualMachineComPort(object):
  def __init__(self, machine_id, comport_id):
    self.machine_id = machine_id
    self.comport_id = comport_id

  @property
  async def properties(self):
    return parse_properties(
      await exec_powershell_checked(
        _ADAPTER_GET_CONCRETE_COMPORT_CMD.format(VM_ID=self.machine_id, COMPORT_ID=self.comport_id)))

  @property
  async def name(self) -> str:
    props = await self.properties
    return props['Name']

  @property
  async def path(self) -> str:
    return (await self.properties)['Path']


DEFAULT_WAIT_OP_TIMEOUT = 60


class ShutdownComponent(ManagementObjectHolder):
  def InitiateShutdown(self, Force, Reason):
    out_objects = self.invoke("InitiateShutdown", Force=Force, Reason=Reason)
    return self._evaluate_invocation_result(
      out_objects,
      ShutdownComponent_ShutdownComponent_ReturnCodes,
      ShutdownComponent_ShutdownComponent_ReturnCodes.Completed_with_No_Error,
      ShutdownComponent_ShutdownComponent_ReturnCodes.Method_Parameters_Checked_JobStarted
    )

  @classmethod
  def from_moh(cls, moh: ManagementObjectHolder) -> 'ShutdownComponent':
    return cls._create_cls_from_moh(cls, 'Msvm_ShutdownComponent', moh)


class VirtualMachine(ManagementObjectHolder):
  """
  Represents virtual machine. Gives access to machine name and id, network adapters, gives ability to start,
  stop, pause, save, reset machine.
  """
  LOG = logging.getLogger('%s.%s' % (__module__, __qualname__))

  def apply_properties(self, class_name: str, properties: Dict[str, Any]):
    """
    Apply ``properties`` for ``class_name`` that associated with virtual machine.

    :param class_name: class name that will be used for modification
    :param properties: properties to apply
    """
    header, footer = _CLS_MAP[class_name]
    cmd = header.format(VM_ID=self.id)
    cmd += _generate_wmi_properties_setters(properties)
    cmd += footer + _JOB_HANDLER_FOOTER
    exec_powershell_checked(cmd)

  def apply_properties_group(self, properties_group: Dict[str, Dict[str, Any]]):
    """
    Applies given properties to virtual machine.

    :param properties_group: dict of classes and their properties
    """
    for cls, properties in sorted(properties_group.items(), key=lambda itm: _CLS_MAP_PRIORITY.get(itm[0], 100)):
      self.apply_properties(cls, properties)

  @property
  def name(self) -> str:
    """
    Virtual machine name that displayed everywhere in windows UI and other places.

    :return: virtual machine name
    """
    return self.properties['ElementName']

  @property
  def id(self) -> str:
    """
    Unique virtual machine identifier.

    :return: virtual machine identifier
    """
    return self.properties['Name']

  @property
  def state(self) -> VirtualMachineState:
    """
    Current virtual machine state. It will try to get actual real state(like running, stopped, etc) for
    ``DEFAULT_WAIT_OP_TIMEOUT`` seconds before returning ``VirtualMachineState.UNDEFINED``. We need this
    ``DEFAULT_WAIT_OP_TIMEOUT`` because hyper-v likes some middle states, like starting, stopping, etc.
    Usually this middle states long not more that 10 seconds and soon will changed to something that we expecting.

    :return: virtual machine state
    """
    _start = time.time()
    state = self._enabled_state.to_virtual_machine_state()
    while state == VirtualMachineState.UNDEFINED and time.time() - _start < DEFAULT_WAIT_OP_TIMEOUT:
      state = self._enabled_state.to_virtual_machine_state()
      time.sleep(.1)
    return state

  def start(self):
    """
    Try to start virtual machine and wait for started state for ``timeout`` seconds.
    """
    if self.state != VirtualMachineState.RUNNING:
      self.LOG.debug("Starting machine '%s'", self.id)
      desired_state = ComputerSystem_RequestStateChange_RequestedState.Running
      target_enabled_state = desired_state.to_ComputerSystem_EnabledState()
      self.RequestStateChange(desired_state)
      if not self._wait_for_enabled_state(target_enabled_state, timeout=DEFAULT_WAIT_OP_TIMEOUT):
        raise Exception("Failed to put machine to '%s' in %s seconds" % (target_enabled_state, DEFAULT_WAIT_OP_TIMEOUT))
      self.LOG.debug("Started machine '%s'", self.id)
    else:
      self.LOG.debug("Machine '%s' is already started", self.id)

  def stop(self, force=False, hard=False):
    """
    Try to stop virtual machine and wait for stopped state for ``timeout`` seconds.

    :param force: indicates if we need to wait for user programs completion, ignored if *force* is *True*
    :param hard: indicates if we need to perform turn off(power off)
    """
    self.LOG.debug("Stopping machine '%s'", self.id)
    desired_state = ComputerSystem_RequestStateChange_RequestedState.Off
    target_enabled_state = desired_state.to_ComputerSystem_EnabledState()
    if not hard:
      shutdown_component = self._get_shutdown_component()
      if shutdown_component:
        shutdown_component.InitiateShutdown(force, "hvapi shutdown")
        if not self._wait_for_enabled_state(target_enabled_state, timeout=DEFAULT_WAIT_OP_TIMEOUT):
          self.LOG.debug("Failed to stop machine '%s' gracefully, killing...", self.id)
          self.kill()
      else:
        self.LOG.debug("Graceful stop for machine '%s' not available, killing...", self.id)
        self.kill()
    else:
      self.kill()
    self.LOG.debug("Stopped machine '%s'", self.id)

  def kill(self):
    """
    Hard-kill vm.
    """
    desired_state = ComputerSystem_RequestStateChange_RequestedState.Off
    target_enabled_state = desired_state.to_ComputerSystem_EnabledState()
    self.RequestStateChange(desired_state)
    if not self._wait_for_enabled_state(target_enabled_state, timeout=DEFAULT_WAIT_OP_TIMEOUT):
      raise Exception("Failed to put machine to '%s' in %s seconds" % (target_enabled_state, DEFAULT_WAIT_OP_TIMEOUT))

  def save(self):
    """
    Try to save virtual machine state and wait for saved state for ``timeout`` seconds.
    """
    if self.state != VirtualMachineState.SAVED:
      self.LOG.debug("Saving machine '%s'", self.id)
      desired_state = ComputerSystem_RequestStateChange_RequestedState.Saved
      target_enabled_state = desired_state.to_ComputerSystem_EnabledState()
      self.RequestStateChange(desired_state)
      if not self._wait_for_enabled_state(target_enabled_state, timeout=DEFAULT_WAIT_OP_TIMEOUT):
        raise Exception("Failed to put machine to '%s' in %s seconds" % (target_enabled_state, DEFAULT_WAIT_OP_TIMEOUT))
      self.LOG.debug("Saved machine '%s'", self.id)
    else:
      self.LOG.debug("Machine '%s' is already saved", self.id)

  def pause(self):
    if self.state != VirtualMachineState.PAUSED:
      self.LOG.debug("Pausing machine '%s'", self.id)
      desired_state = ComputerSystem_RequestStateChange_RequestedState.Paused
      target_enabled_state = desired_state.to_ComputerSystem_EnabledState()
      self.RequestStateChange(desired_state)
      if not self._wait_for_enabled_state(target_enabled_state, timeout=DEFAULT_WAIT_OP_TIMEOUT):
        raise Exception("Failed to put machine to '%s' in %s seconds" % (target_enabled_state, DEFAULT_WAIT_OP_TIMEOUT))
      self.LOG.debug("Paused machine '%s'", self.id)
    else:
      self.LOG.debug("Machine '%s' is already paused", self.id)

  def connect_to_switch(self, virtual_switch: 'VirtualSwitch', static_mac=None) -> 'VirtualMachineNetworkAdapter':
    """
    Connects machine to given ``VirtualSwitch``.

    :param static_mac: static mac that will be assigned, None will set dynamic one
    :param virtual_switch: virtual switch to connect
    """
    Msvm_ResourcePool = self.scope_holder.query_one(
      "SELECT * FROM Msvm_ResourcePool WHERE ResourceSubType = 'Microsoft:Hyper-V:Synthetic Ethernet Port' "
      "AND Primordial = True"
    )
    Msvm_SyntheticEthernetPortSettingData_Path = (
      Node(Relation.RELATED,
           ("Msvm_AllocationCapabilities", "Msvm_ElementCapabilities", None, None, None, None, False, None)),
      Node(Relation.RELATIONSHIP, "Msvm_SettingsDefineCapabilities", selector=PropertySelector('ValueRole', 0)),
      Node(Relation.PROPERTY, "PartComponent", (Property.SINGLE, MOHTransformers.from_reference))
    )
    Msvm_SyntheticEthernetPortSettingData = Msvm_ResourcePool.traverse(Msvm_SyntheticEthernetPortSettingData_Path)
    pass

  def is_connected_to_switch(self, virtual_switch: 'VirtualSwitch'):
    """
    Returns ``True`` if machine is connected to given ``VirtualSwitch``.

    :param virtual_switch: virtual switch to check connection
    :return: ``True`` if connected, otherwise ``False``
    """
    pass

  def add_vhd_disk(self, vhd_disk: VHDDisk):
    """
    Adds given ``VHDDisk`` to virtual machine.

    :param vhd_disk: ``VHDDisk`` to add to machine
    """
    pass

  @property
  def network_adapters(self) -> List[VirtualMachineNetworkAdapter]:
    """
    Returns list of machines network adapters.

    :return: list of machines network adapters
    """
    result = []
    port_to_switch_path = (
      VirtualSystemSettingDataNode,
      Node(Relation.RELATED, "Msvm_SyntheticEthernetPortSettingData"),
    )
    for _, seps in self.traverse(port_to_switch_path):
      result.append(VirtualMachineNetworkAdapter.from_moh(seps))
    return result

  @property
  def com_ports(self) -> List[VirtualMachineComPort]:
    pass

  def add_com_port(self, number, path):
    pass

  # internal methods
  def _wait_for_enabled_state(self, awaitable_state, timeout=DEFAULT_WAIT_OP_TIMEOUT):
    _start = time.time()
    while self._enabled_state != awaitable_state and time.time() - _start < timeout:
      time.sleep(1)
    return self._enabled_state == awaitable_state

  def _get_shutdown_component(self):
    shutdown_component_traverse_result = self.traverse((Node(Relation.RELATED, "Msvm_ShutdownComponent"),))
    if shutdown_component_traverse_result:
      shutdown_component = shutdown_component_traverse_result[-1][-1]
      operational_status = ShutdownComponent_OperationalStatus.from_code(
        shutdown_component.properties['OperationalStatus'][0])
      if operational_status in (ShutdownComponent_OperationalStatus.OK, ShutdownComponent_OperationalStatus.Degraded):
        return ShutdownComponent.from_moh(shutdown_component)
    return None

  @property
  def _enabled_state(self) -> ComputerSystem_EnabledState:
    self.reload()
    return ComputerSystem_EnabledState.from_code(self.properties['EnabledState'])

  # WMI object methods
  def RequestStateChange(self, RequestedState: ComputerSystem_RequestStateChange_RequestedState, TimeoutPeriod=None):
    out_objects = self.invoke("RequestStateChange", RequestedState=RequestedState.value, TimeoutPeriod=TimeoutPeriod)
    return self._evaluate_invocation_result(
      out_objects,
      ComputerSystem_RequestStateChange_ReturnCodes,
      ComputerSystem_RequestStateChange_ReturnCodes.Completed_with_No_Error,
      ComputerSystem_RequestStateChange_ReturnCodes.Method_Parameters_Checked_Transition_Started
    )

  @classmethod
  def from_moh(cls, moh: ManagementObjectHolder) -> 'VirtualMachine':
    return cls._create_cls_from_moh(cls, 'Msvm_ComputerSystem', moh)


class HypervHost(object):
  def __init__(self, scope=None):
    self.scope = scope
    if not self.scope:
      self.scope = ScopeHolder()

  @property
  def switches(self) -> List[VirtualSwitch]:
    machines = self.scope.query('SELECT * FROM Msvm_VirtualEthernetSwitch')
    return [VirtualSwitch.from_moh(_machine) for _machine in machines] if machines else []

  def switches_by_name(self, name) -> VirtualSwitch:
    machines = self.scope.query('SELECT * FROM Msvm_VirtualEthernetSwitch AND ElementName = "%s"' % name)
    return [VirtualSwitch.from_moh(_machine) for _machine in machines] if machines else []

  def switch_by_id(self, switch_id) -> VirtualSwitch:
    machines = self.scope.query('SELECT * FROM Msvm_VirtualEthernetSwitch AND Name = "%s"' % switch_id)
    return [VirtualSwitch.from_moh(_machine) for _machine in machines] if machines else []

  @property
  def machines(self) -> List[VirtualMachine]:
    machines = self.scope.query('SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine"')
    return [VirtualMachine.from_moh(_machine) for _machine in machines] if machines else []

  def machines_by_name(self, name) -> List[VirtualMachine]:
    machines = self.scope.query(
      'SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine" AND ElementName = "%s"' % name)
    return [VirtualMachine.from_moh(_machine) for _machine in machines] if machines else []

  def machine_by_id(self, machine_id) -> VirtualMachine:
    machines = self.scope.query(
      'SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine" AND Name = "%s"' % machine_id)
    return [VirtualMachine.from_moh(_machine) for _machine in machines] if machines else []

  def create_machine(self, name, properties_group: Dict[str, Dict[str, Any]] = None,
                     machine_generation: VirtualMachineGeneration = VirtualMachineGeneration.GEN1) -> VirtualMachine:
    pass
