import logging
import time
from enum import Enum
from typing import List, Dict, Any

from hvapi.hv_types_internal import VirtualMachineStateInternal
from hvapi.powershell_utils import parse_properties, exec_powershell_checked, parse_select_object_output

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
_MACHINE_CONNECT_TO_SWITCH_CMD = 'Add-VMNetworkAdapter -VMName "{VM_NAME}" -SwitchName "{SWITCH_NAME}"'
_MACHINE_ADD_VHD_CMD = 'Add-VMHardDiskDrive -VMName "{VM_NAME}" -Path "{VHD_PATH}"'
_MACHINE_GET_PROPERTY_CMD = '(Get-Vm -Id {ID}).{PROPERTY}'
_MACHINE_STOP_FORCE_CMD = 'Stop-VM -VM (Get-Vm -Id {ID}) -Force'
_MACHINE_START_CMD = 'Start-VM -VM (Get-Vm -Id {ID})'
_MACHINE_SAVE_CMD = 'Save-VM -VM (Get-Vm -Id {ID})'
_MACHINE_PAUSE_CMD = 'Suspend-VM -VM (Get-Vm -Id {ID})'
_MACHINE_ADD_COMPORT_CMD = 'Set-VMComPort -VM (Get-Vm -Id {ID}) -Number {NUMBER} -Path {PATH}'

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
  GEN1 = "Microsoft:Hyper-V:SubType:1"
  GEN2 = "Microsoft:Hyper-V:SubType:2"


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


class VirtualSwitch(object):
  def __init__(self, switch_id, switch_name):
    self.switch_id = switch_id
    self.switch_name = switch_name

  @property
  def name(self):
    return self.switch_name

  @property
  def id(self):
    return self.switch_id

  def __eq__(self, other):
    return self.id == other.id and self.name == other.name


class VirtualMachineNetworkAdapter(object):
  def __init__(self, machine_id, adapter_id):
    self.machine_id = machine_id
    self.adapter_id = adapter_id

  @property
  async def properties(self):
    return parse_properties(
      await exec_powershell_checked(
        _ADAPTER_GET_CONCRETE_ADAPTER_CMD.format(VM_ID=self.machine_id, ADAPTER_ID=self.adapter_id)))

  @property
  async def address(self) -> str:
    return (await self.properties)['MacAddress']

  @property
  async def switch(self) -> 'VirtualSwitch':
    props = await self.properties
    return VirtualSwitch(props['SwitchId'], props['SwitchName'])


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


class VirtualMachine(object):
  """
  Represents virtual machine. Gives access to machine name and id, network adapters, gives ability to start,
  stop, pause, save, reset machine.
  """
  LOG = logging.getLogger('%s.%s' % (__module__, __qualname__))

  def __init__(self, machine_id: str, name: str):
    self.machine_id = machine_id
    self.machine_name = name

  async def apply_properties(self, class_name: str, properties: Dict[str, Any]):
    """
    Apply ``properties`` for ``class_name`` that associated with virtual machine.

    :param class_name: class name that will be used for modification
    :param properties: properties to apply
    """
    header, footer = _CLS_MAP[class_name]
    cmd = header.format(VM_ID=self.id)
    cmd += _generate_wmi_properties_setters(properties)
    cmd += footer + _JOB_HANDLER_FOOTER
    await exec_powershell_checked(cmd)

  async def apply_properties_group(self, properties_group: Dict[str, Dict[str, Any]]):
    """
    Applies given properties to virtual machine.

    :param properties_group: dict of classes and their properties
    """
    for cls, properties in sorted(properties_group.items(), key=lambda itm: _CLS_MAP_PRIORITY.get(itm[0], 100)):
      await self.apply_properties(cls, properties)

  @property
  def name(self) -> str:
    """
    Virtual machine name that displayed everywhere in windows UI and other places.

    :return: virtual machine name
    """
    return self.machine_name

  @property
  def id(self) -> str:
    """
    Unique virtual machine identifier.

    :return: virtual machine identifier
    """
    return self.machine_id

  @property
  async def state(self, timeout=30) -> VirtualMachineState:
    """
    Current virtual machine state. It will try to get actual real state(like running, stopped, etc) for ``timeout``
    seconds before returning ``VirtualMachineState.UNDEFINED``. We need this ``timeout`` because hyper-v likes some
    middle states, like starting, stopping, etc. Usually this middle states long not more that 10 seconds and soon will
    changed to something that we expecting.

    :param timeout: time to wait for real state
    :return: virtual machine state
    """
    _start = time.time()
    state = VirtualMachineStateInternal[
      (await exec_powershell_checked(_MACHINE_GET_PROPERTY_CMD.format(ID=self.id, PROPERTY='State'))).strip()
    ].to_virtual_machine_state()
    while state == VirtualMachineState.UNDEFINED and time.time() - _start < timeout:
      state = VirtualMachineStateInternal[
        (await exec_powershell_checked(_MACHINE_GET_PROPERTY_CMD.format(ID=self.id, PROPERTY='State'))).strip()
      ].to_virtual_machine_state()
      time.sleep(1)
    return state

  async def start(self):
    """
    Try to start virtual machine and wait for started state for ``timeout`` seconds.

    :param timeout: time to wait for started state
    """
    await exec_powershell_checked(_MACHINE_START_CMD.format(ID=self.id))

  async def stop(self, hard=False, timeout=60):
    """
    Try to stop virtual machine and wait for stopped state for ``timeout`` seconds. If ``hard`` equals to ``False``
    graceful stop will be performed. This function can wait twice of ``timeout`` value in case ``hard=False``, first
    time it will wait for graceful stop and second - for hard stop.

    :param hard: indicates if we need to perform hard stop
    :param timeout: time to wait for stopped state
    """
    # TODO implement soft stop
    if hard:
      await exec_powershell_checked(_MACHINE_STOP_FORCE_CMD.format(ID=self.id))
    else:
      await exec_powershell_checked(_MACHINE_STOP_FORCE_CMD.format(ID=self.id))

  async def save(self):
    """
    Try to save virtual machine state and wait for saved state for ``timeout`` seconds.

    :param timeout: time to wait for saved state
    """
    await exec_powershell_checked(_MACHINE_SAVE_CMD.format(ID=self.id))

  async def pause(self):
    await exec_powershell_checked(_MACHINE_PAUSE_CMD.format(ID=self.id))

  async def connect_to_switch(self, virtual_switch: 'VirtualSwitch'):
    """
    Connects machine to given ``VirtualSwitch``.

    :param virtual_switch: virtual switch to connect
    """
    if not self.is_connected_to_switch(virtual_switch):
      await exec_powershell_checked(
        _MACHINE_CONNECT_TO_SWITCH_CMD.format(VM_NAME=self.name, SWITCH_NAME=virtual_switch.name)
      )

  async def is_connected_to_switch(self, virtual_switch: 'VirtualSwitch'):
    """
    Returns ``True`` if machine is connected to given ``VirtualSwitch``.

    :param virtual_switch: virtual switch to check connection
    :return: ``True`` if connected, otherwise ``False``
    """
    for adapter in await self.network_adapters:
      if await adapter.switch == virtual_switch:
        return True
    return False

  async def add_vhd_disk(self, vhd_disk: VHDDisk):
    """
    Adds given ``VHDDisk`` to virtual machine.

    :param vhd_disk: ``VHDDisk`` to add to machine
    """
    await exec_powershell_checked(_MACHINE_ADD_VHD_CMD.format(VM_NAME=self.name, VHD_PATH=vhd_disk.vhd_file_path))

  @property
  async def network_adapters(self) -> List[VirtualMachineNetworkAdapter]:
    """
    Returns list of machines network adapters.

    :return: list of machines network adapters
    """
    result = []
    adapter_properties_list = await parse_select_object_output(
      _MACHINE_GET_MACHINE_ADAPTERS_CMD.format(VM_ID=self.id),
      delimiter="--------------------"
    )
    for adapter_properties in adapter_properties_list:
      result.append(VirtualMachineNetworkAdapter(self.id, adapter_properties['Id']))
    return result

  @property
  async def com_ports(self) -> List[VirtualMachineComPort]:
    result = []
    comports_properties_list = await parse_select_object_output(
      _MACHINE_GET_MACHINE_COMPORTS_CMD.format(VM_ID=self.id),
      delimiter="--------------------"
    )
    for comport_properties in comports_properties_list:
      result.append(VirtualMachineComPort(self.id, comport_properties['Id']))
    return result

  async def add_com_port(self, number, path):
    await exec_powershell_checked(_MACHINE_ADD_COMPORT_CMD.format(ID=self.id, NUMBER=number, PATH=path))


class HypervHost(object):
  @property
  async def switches(self) -> List[VirtualSwitch]:
    return await self._common_get(_HOST_ALL_SWITCHES_CMD, VirtualSwitch, ("Id", "Name"))

  async def switches_by_name(self, name) -> VirtualSwitch:
    return await self._common_get(_HOST_SWITCH_BY_NAME_CMD.format(NAME=name), VirtualSwitch, ("Id", "Name"))

  async def switch_by_id(self, switch_id) -> VirtualSwitch:
    switches = await self._common_get(_HOST_SWITCH_BY_ID_CMD.format(ID=switch_id), VirtualSwitch, ("Id", "Name"))
    if switches:
      return switches[0]

  @property
  async def machines(self) -> List[VirtualMachine]:
    return await self._common_get(_HOST_ALL_MACHINES_CMD, VirtualMachine, ("VMId", "VMName"))

  async def machines_by_name(self, name) -> List[VirtualMachine]:
    return await self._common_get(_HOST_MACHINE_BY_NAME_CMD.format(NAME=name), VirtualMachine, ("VMId", "VMName"))

  async def machine_by_id(self, machine_id) -> VirtualMachine:
    machines = await self._common_get(_HOST_MACHINE_BY_ID_CMD.format(ID=machine_id), VirtualMachine, ("VMId", "VMName"))
    if machines:
      return machines[0]

  async def create_machine(self, name, properties_group: Dict[str, Dict[str, Any]] = None,
                           machine_generation: VirtualMachineGeneration = VirtualMachineGeneration.GEN1) -> VirtualMachine:
    # TODO implement
    pass

  @staticmethod
  async def _common_get(cmd, cls, properties):
    machine_properties_list = await parse_select_object_output(cmd, delimiter="--------------------")
    result = []
    for machine_properties in machine_properties_list:
      props = [machine_properties[prop] for prop in properties]
      result.append(cls(*props))
    return result
