import logging
import time
from typing import List

from hvapi.wmi_utils import WmiHelper, get_wmi_object_properties, wait_for_wmi_job, IntEnum, RangedCodeEnum, Node, Path, \
  management_object_traversal


class WmiObjectWrapper(object):
  def __init__(self, wmi_object, wmi_helper: WmiHelper):
    self.wmi_object = wmi_object
    self.wmi_helper = wmi_helper

  @property
  def properties(self):
    return get_wmi_object_properties(self.wmi_object)

  def reload(self):
    """
    Reload wmi object. Use to update properties values.
    """
    self.wmi_object = self.wmi_helper.get(self.wmi_object.path_())

  def __eq__(self, other):
    if isinstance(other, VirtualSwitch):
      return self.wmi_object == other.wmi_object
    return False


class VirtualSwitch(WmiObjectWrapper):
  @property
  def name(self):
    return self.wmi_object.ElementName

  @property
  def id(self):
    return self.wmi_object.Name


class _ComputerSystemEnabledState(IntEnum):
  """
  For internal usage only. Represents actual state of Machine. It is Msvm_ComputerSystem.EnabledState property.
  """
  Unknown = 0
  Other = 1
  Enabled = 2  # running
  Disabled = 3  # stopped
  ShuttingDown = 4
  NotApplicable = 5
  EnabledButOffline = 6  # saved
  InTest = 7
  Deferred = 8
  Quiesce = 9  # paused
  Starting = 10


class _ComputerSystemRequestedState(IntEnum):
  """
  For internal usage only. Passed to Msvm_ComputerSystem.RequestStateChange method call.
  """
  Other = 1
  Running = 2
  Off = 3
  Stopping = 4
  Saved = 6
  Paused = 9
  Starting = 10
  Reset = 11
  Saving = 32773
  Pausing = 32776
  Resuming = 32777
  FastSaved = 32779
  FastSaving = 32780


class _ShutdownComponentOperationalStatus(IntEnum):
  """
  For internal usage only. Msvm_ShutdownComponent.OperationalStatus property.
  """
  OK = 2
  Degraded = 3
  NonRecoverableError = 7
  NoContact = 12
  LostCommunication = 13


class _ComputerSystemRequestStateChangeCodes(RangedCodeEnum):
  """
  For internal usage only. Msvm_ComputerSystem.RequestStateChange method call error codes.
  """
  CompletedWithNoError = (0,)
  MethodParametersChecked_TransitionStarted = (4096,)
  AccessDenied = (32769,)
  InvalidStateForThisOperation = (32775,)


class _VirtualSystemManagementServiceModificationCodes(RangedCodeEnum):
  """
  For internal usage only. Msvm_VirtualSystemManagementService.[ModifySystemSettings, ModifyResourceSettings] method
  call error codes.
  """
  CompletedWithNoError = (0,)
  NotSupported = (1,)
  Failed = (2,)
  Timeout = (3,)
  InvalidParameter = (4,)
  InvalidState = (5,)
  IncompatibleParameters = (6,)
  MethodParametersChecked_TransitionStarted = (4096,)
  MethodReserved = (4097, 32767)
  VendorSpecific = (32768, 65535)


class VirtualMachine(WmiObjectWrapper):
  LOG = logging.getLogger('%s.%s' % (__module__, __qualname__))

  @property
  def dynamic_memory(self):
    memory_settings_path = (
      Node(Path.RELATED, "Msvm_VirtualSystemSettingData"),
      Node(Path.RELATED, "Msvm_MemorySettingData"),
    )
    _, msd = management_object_traversal(memory_settings_path, self.wmi_object)[0]
    return msd.DynamicMemoryEnabled

  @dynamic_memory.setter
  def dynamic_memory(self, value: bool):
    memory_settings_path = (
      Node(Path.RELATED, "Msvm_VirtualSystemSettingData"),
      Node(Path.RELATED, "Msvm_MemorySettingData"),
    )
    management_service = self.wmi_helper.query_one('SELECT * FROM Msvm_VirtualSystemManagementService')
    vssd, msd = management_object_traversal(memory_settings_path, self.wmi_object)[0]
    if value:
      msd.DynamicMemoryEnabled = True
      vssd.VirtualNumaEnabled = False
      # save modified resource
      self._call_object_method(
        management_service,
        "ModifySystemSettings",
        lambda x: _VirtualSystemManagementServiceModificationCodes.from_code(x[1]),
        _VirtualSystemManagementServiceModificationCodes.CompletedWithNoError,
        SystemSettings=vssd.GetText_(2)
      )
    else:
      msd.DynamicMemoryEnabled = False

    # save modified resource
    self._call_object_method(
      management_service,
      "ModifyResourceSettings",
      lambda x: _VirtualSystemManagementServiceModificationCodes.from_code(x[2]),
      _VirtualSystemManagementServiceModificationCodes.CompletedWithNoError,
      ResourceSettings=[msd.GetText_(2)]
    )

  @property
  def name(self) -> str:
    """
    Virtual machine name that displayed everywhere in windows UI and other places.

    :return: virtual machine name
    """
    return self.wmi_object.ElementName

  @property
  def id(self) -> str:
    """
    Unique virtual machine identifier.

    :return: virtual machine identifier
    """
    return self.wmi_object.Name

  @property
  def state(self) -> _ComputerSystemEnabledState:
    """
    Current virtual machine state.

    :return: virtual machine state
    """
    self.reload()
    return _ComputerSystemEnabledState.from_code(self.wmi_object.EnabledState)

  def start(self, timeout=60):
    """
    Try to start virtual machine and wait for started state for ``timeout`` seconds.

    :param timeout: time to wait for started state
    """
    self.LOG.debug("Starting machine '%s'", self.id)
    self._request_machine_state(_ComputerSystemRequestedState.Running)
    if not self.wait_for_state(_ComputerSystemEnabledState.Enabled, timeout=timeout):
      raise Exception("Failed to put machine to '%s' in %s seconds" % (_ComputerSystemEnabledState.Enabled, timeout))
    self.LOG.debug("Started machine '%s'", self.id)

  def save(self, timeout=60):
    """
    Try to save virtual machine state and wait for saved state for ``timeout`` seconds.

    :param timeout: time to wait for saved state
    """
    self.LOG.debug("Saving machine '%s'", self.id)
    self._request_machine_state(_ComputerSystemRequestedState.Saved)
    if not self.wait_for_state(_ComputerSystemEnabledState.EnabledButOffline, timeout=60):
      raise Exception(
        "Failed to put machine to '%s' in %s seconds" % (_ComputerSystemEnabledState.EnabledButOffline, timeout))
    self.LOG.debug("Saved machine '%s'", self.id)

  def stop(self, hard=False, timeout=60):
    """
    Try to stop virtual machine and wait for stopped state for ``timeout`` seconds. If ``hard`` equals to ``False``
    graceful stop will be performed. This function can wait twice of ``timeout`` value in case ``hard=False``, first
    time it will wait for graceful stop and second - for hard stop.

    :param hard: indicates if we need to perform hard stop
    :param timeout: time to wait for stopped state
    """
    self.LOG.debug("Stopping machine '%s'", self.id)
    if not hard:
      shutdown_component = self._get_shutdown_component()
      if shutdown_component:
        result = shutdown_component.InitiateShutdown(True, "hyper-v api shutdown")
        if result[0] != 0 or (
                result[0] == 0 and not self.wait_for_state(_ComputerSystemEnabledState.Disabled, timeout=timeout)):
          self.LOG.debug("Failed to gracefully stop machine '%s', killing it", self.id)
          self._request_machine_state(_ComputerSystemRequestedState.Off)
    else:
      self._request_machine_state(_ComputerSystemRequestedState.Off)
    if not self.wait_for_state(_ComputerSystemEnabledState.Disabled, timeout=timeout):
      raise Exception(
        "Failed to put machine to '%s' in %s seconds" % (_ComputerSystemEnabledState.EnabledButOffline, timeout))
    self.LOG.debug("Stopped machine '%s'", self.id)

  def wait_for_state(self, state: _ComputerSystemEnabledState, timeout=60):
    """
    Wait for given ``state`` of machine.

    :param state: state to wait for
    :param timeout: time to wait for state
    :return: ``True`` if given ``state`` reached in ``timeout`` seconds, otherwise ``False``
    """

    def _while_condition(start_time=None):
      if timeout:
        return (time.time() - start_time) < timeout
      return True

    _begin = time.time()
    while _while_condition(_begin):
      if state == self.state:
        return True
      time.sleep(0.5)
    return state == self.state

  # PRIVATE
  def _call_object_method(self, obj, method_name, err_code_getter, expected_value, *args, **kwargs):
    method = getattr(obj, method_name)
    result = method(*args, **kwargs)
    result_value = err_code_getter(result)
    if result_value != expected_value:
      msg = "%s.%s failed with %s" % (obj.Path_.Class, method_name, result_value)
      self.LOG.error(msg)
      raise Exception(msg)

  def _request_machine_state(self, desired_state: _ComputerSystemRequestedState):
    job, ret_code = self.wmi_object.RequestStateChange(desired_state.value)
    rscc = _ComputerSystemRequestStateChangeCodes.from_code(ret_code)
    if rscc not in (_ComputerSystemRequestStateChangeCodes.CompletedWithNoError,
                    _ComputerSystemRequestStateChangeCodes.MethodParametersChecked_TransitionStarted):
      raise Exception("Failed to change machine state to '%s' with result '%s'" % (desired_state, rscc))
    if rscc == _ComputerSystemRequestStateChangeCodes.MethodParametersChecked_TransitionStarted:
      wait_for_wmi_job(job)
    self.LOG.debug("Requested state '%s' of machine '%s' successfully", desired_state, self.id)

  def _get_shutdown_component(self):
    shutdown_component = self.wmi_object.associators(wmi_result_class="Msvm_ShutdownComponent")
    if shutdown_component:
      shutdown_component = shutdown_component[0]
      operational_status = _ShutdownComponentOperationalStatus.from_code(shutdown_component.OperationalStatus[0])
      if operational_status in (_ShutdownComponentOperationalStatus.OK, _ShutdownComponentOperationalStatus.Degraded):
        return shutdown_component


class HypervHost(object):
  def __init__(self):
    self.wmi_helper = WmiHelper()

  @property
  def switches(self) -> List[VirtualSwitch]:
    return [VirtualSwitch(wmi_obj, self.wmi_helper) for wmi_obj in
            self.wmi_helper.query("SELECT * FROM Msvm_VirtualEthernetSwitch")]

  def switch_by_name(self, name) -> VirtualSwitch:
    result = self.wmi_helper.query(
      'SELECT * FROM Msvm_VirtualEthernetSwitch WHERE ElementName = "%s"' % name)
    if len(result) > 1:
      raise Exception(
        "There are too much(%d) virtual switches with name '%s', use id instead" % (len(result), name))
    if result:
      return result[0]

  def switch_by_id(self, switch_id) -> VirtualSwitch:
    result = self.wmi_helper.query(
      'SELECT * FROM Msvm_VirtualEthernetSwitch WHERE Name = "%s"' % switch_id)
    if result:
      return result[0]

  @property
  def machines(self) -> List[VirtualMachine]:
    return [VirtualMachine(wmi_obj, self.wmi_helper) for wmi_obj in
            self.wmi_helper.query('SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine"')]

  def machine_by_name(self, name) -> VirtualMachine:
    result = self.wmi_helper.query(
      'SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine" AND ElementName = "%s"' % name)
    if len(result) > 1:
      raise Exception(
        "There are too much(%d) virtual machines with name '%s', use id instead" % (len(result), name))
    if result:
      return VirtualMachine(result[0], self.wmi_helper)

  def machine_by_id(self, machine_id) -> VirtualMachine:
    result = self.wmi_helper.query(
      'SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine" AND Name = "%s"' % machine_id)
    if result:
      return VirtualMachine(result[0], self.wmi_helper)
