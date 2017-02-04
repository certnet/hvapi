from typing import List

import time

from hvapi.wmi_utils import WmiHelper, get_wmi_object_properties, wait_for_wmi_job, \
  IntEnum, RangedCodeEnum

HYPERV_VM_STATE_ENABLED = 2
HYPERV_VM_STATE_DISABLED = 3
HYPERV_VM_STATE_REBOOT = 10
HYPERV_VM_STATE_RESET = 11
HYPERV_VM_STATE_PAUSED = 32768
HYPERV_VM_STATE_SUSPENDED = 32769


class WmiObjectWrapper(object):
  def __init__(self, wmi_object, wmi_helper: WmiHelper):
    self.wmi_object = wmi_object
    self.wmi_helper = wmi_helper

  @property
  def properties(self):
    return get_wmi_object_properties(self.wmi_object)

  def reload(self):
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


class VirtualMachine(WmiObjectWrapper):
  class EnabledState(IntEnum):
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

  class RequestedState(IntEnum):
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

  class ShutdownComponentOperationalStatus(IntEnum):
    """
    For internal usage only. Msvm_ShutdownComponent.OperationalStatus property.
    """
    OK = 2
    Degraded = 3
    NonRecoverableError = 7
    NoContact = 12
    LostCommunication = 13

  class RequestStateChangeCodes(RangedCodeEnum):
    """
    For internal usage only. Msvm_ComputerSystem.RequestStateChange method call error codes.
    """
    CompletedWithNoError = (0,)
    MethodParametersChecked_TransitionStarted = (4096,)
    AccessDenied = (32769,)
    InvalidStateForThisOperation = (32775,)

  @property
  def name(self):
    return self.wmi_object.ElementName

  @property
  def id(self):
    return self.wmi_object.Name

  def _change_machine_state(self, desired_state):
    job, ret_code = self.wmi_object.RequestStateChange(desired_state.value)
    rscc = self.RequestStateChangeCodes.from_code(ret_code)
    if rscc not in (self.RequestStateChangeCodes.CompletedWithNoError,
                    self.RequestStateChangeCodes.MethodParametersChecked_TransitionStarted):
      raise Exception("Failed to change machine state to '%s' with result '%s'" % (desired_state, rscc))
    if rscc == self.RequestStateChangeCodes.MethodParametersChecked_TransitionStarted:
      wait_for_wmi_job(job)

  def _get_shutdown_component(self):
    shutdown_component = self.wmi_object.associators(wmi_result_class="Msvm_ShutdownComponent")
    if shutdown_component:
      shutdown_component = shutdown_component[0]
      operational_status = self.ShutdownComponentOperationalStatus.from_code(shutdown_component.OperationalStatus[0])
      if operational_status in (
          self.ShutdownComponentOperationalStatus.OK, self.ShutdownComponentOperationalStatus.Degraded):
        return shutdown_component

  def start(self):
    self._change_machine_state(self.RequestedState.Running)
    if not self.wait_for_state(self.EnabledState.Enabled, timeout=60):
      raise Exception("Failed to put machine to '%s' in 60 seconds" % self.EnabledState.Enabled)

  def save(self):
    self._change_machine_state(self.RequestedState.Saved)

  def stop(self, hard=False):
    if not hard:
      shutdown_component = self._get_shutdown_component()
      if shutdown_component:
        result = shutdown_component.InitiateShutdown(True, "hyper-v api shutdown")
        if result[0] != 0 or (result[0] == 0 and not self.wait_for_state(self.EnabledState.Disabled, timeout=60)):
          # TODO log that graceful stop failed
          self._change_machine_state(self.RequestedState.Off)
    else:
      self._change_machine_state(self.RequestedState.Off)

  @property
  def state(self):
    self.reload()
    return self.EnabledState.from_code(self.wmi_object.EnabledState)

  def wait_for_state(self, state: EnabledState, timeout=60):
    def _while_condition(start_time=None):
      if timeout:
        return (time.time() - start_time) < timeout
      return True

    start_time = time.time()
    while _while_condition(start_time):
      if state == self.state:
        return True
    return state == self.state


class HypervHost(object):
  def __init__(self):
    self.wmi_helper = WmiHelper()

  @staticmethod
  def _by_name(item_name, item_collection, item_message):
    result = []
    for item in item_collection:
      if item.name == item_name:
        result.append(item)
    if len(result) > 1:
      raise Exception(
        "There is too much(%d) %s with name '%s', use switch id instead" % (len(result), item_message, item_name))
    return result[0]

  @staticmethod
  def _by_id(item_id, item_collection):
    for item in item_collection:
      if item.id == item_id:
        return item

  @property
  def switches(self) -> List[VirtualSwitch]:
    return [VirtualSwitch(wmi_obj, self.wmi_helper) for wmi_obj in
            self.wmi_helper.query("SELECT * FROM Msvm_VirtualEthernetSwitch")]

  def switch_by_name(self, name) -> VirtualSwitch:
    return self._by_name(name, self.switches, "virtual switches")

  def switch_by_id(self, switch_id) -> VirtualSwitch:
    return self._by_id(switch_id, self.switches)

  @property
  def machines(self) -> List[VirtualMachine]:
    return [VirtualMachine(wmi_obj, self.wmi_helper) for wmi_obj in
            self.wmi_helper.query('SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine"')]

  def machine_by_name(self, name) -> VirtualMachine:
    return self._by_name(name, self.machines, "virtual machines")

  def machine_by_id(self, machine_id) -> VirtualMachine:
    return self._by_id(machine_id, self.machines)


import pprint


def measure_time(func, *args, **kwargs):
  start = time.time()
  try:
    return func(*args, **kwargs)
  finally:
    print("Call took:", time.time() - start)


host = HypervHost()
res = HypervHost()
machine = host.machine_by_name("linux")
# machine.start()
# machine.save()
machine.start()
print(machine.state)
machine.stop()
print(machine.state)
# prev_state = None
# while True:
#   state = machine.state
#   if state != prev_state:
#     print(state)
#   prev_state = state
# pprint.pprint()
# res.stop()
# print(res)
pass
