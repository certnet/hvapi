from hvapi.wmi_utils import IntEnum, RangedCodeEnum


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

  def to_virtual_machine_state(self):
    from hvapi.hyperv import VirtualMachineState
    if self == _ComputerSystemEnabledState.Enabled:
      return VirtualMachineState.RUNNING
    elif self == _ComputerSystemEnabledState.Disabled:
      return VirtualMachineState.STOPPED
    elif self == _ComputerSystemEnabledState.EnabledButOffline:
      return VirtualMachineState.SAVED
    elif self == _ComputerSystemEnabledState.Quiesce:
      return VirtualMachineState.PAUSED
    else:
      return VirtualMachineState.UNDEFINED


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

  # @classmethod
  # def from_virtual_machine_state(cls, vms: 'VirtualMachineState'):
  #   if vms == VirtualMachineState.Running:
  #     return cls.Running
  #   elif vms == VirtualMachineState.STOPPED:
  #     return cls.Off
  #   elif vms == VirtualMachineState.SAVED:
  #     return cls.Saved
  #   elif vms == VirtualMachineState.PAUSED:
  #     return cls.Paused
  #   raise Exception("You doing something wrong, we can not move machine to state '%s'" % vms)


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
