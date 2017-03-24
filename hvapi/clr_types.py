from enum import Enum

from hvapi.common_types import RangedCodeEnum
from hvapi.types import VirtualMachineState


class Msvm_ConcreteJob_JobState(RangedCodeEnum):
  New = 2
  Starting = 3
  Running = 4
  Suspended = 5
  ShuttingDown = 6
  Completed = 7
  Terminated = 8
  Killed = 9
  Exception = 10
  Service = 11
  DMTF_Reserved = (12, 32767)
  Vendor_Reserved = (32768, 65535)


class VirtualMachineStateInternal(str, Enum):
  Other = 'Other'
  Running = 'Running'
  Off = 'Off'
  Stopping = 'Stopping'
  Saved = 'Saved'
  Paused = 'Paused'
  Starting = 'Starting'
  Reset = 'Reset'
  Saving = 'Saving'
  Pausing = 'Pausing'
  Resuming = 'Resuming'
  FastSaved = 'FastSaved'
  FastSaving = 'FastSaving'
  ForceShutdown = 'ForceShutdown'
  ForceReboot = 'ForceReboot'
  RunningCritical = 'RunningCritical'
  OffCritical = 'OffCritical'
  StoppingCritical = 'StoppingCritical'
  SavedCritical = 'SavedCritical'
  PausedCritical = 'PausedCritical'
  StartingCritical = 'StartingCritical'
  ResetCritical = 'ResetCritical'
  SavingCritical = 'SavingCritical'
  PausingCritical = 'PausingCritical'
  ResumingCritical = 'ResumingCritical'
  FastSavedCritical = 'FastSavedCritical'
  FastSavingCritical = 'FastSavingCritical'

  def to_virtual_machine_state(self):
    if self == VirtualMachineStateInternal.Running:
      return VirtualMachineState.RUNNING
    elif self == VirtualMachineStateInternal.Off:
      return VirtualMachineState.STOPPED
    elif self in (VirtualMachineStateInternal.Saved, VirtualMachineStateInternal.FastSaved):
      return VirtualMachineState.SAVED
    elif self == VirtualMachineStateInternal.Paused:
      return VirtualMachineState.PAUSED
    else:
      return VirtualMachineState.UNDEFINED


class ComputerSystem_RequestStateChange_RequestedState(RangedCodeEnum):
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

  def to_ComputerSystem_EnabledState(self):
    if self == self.Other:
      return ComputerSystem_EnabledState.Other
    if self == self.Running:
      return ComputerSystem_EnabledState.Enabled
    if self == self.Off:
      return ComputerSystem_EnabledState.Disabled
    if self == self.Stopping:
      return ComputerSystem_EnabledState.ShuttingDown
    if self == self.Saved:
      return ComputerSystem_EnabledState.EnabledButOffline
    if self == self.Paused:
      return ComputerSystem_EnabledState.Quiesce
    if self == self.Reset:
      return ComputerSystem_EnabledState.Enabled
    raise ValueError("'%s' can not be mapped to ComputerSystem_EnabledState" % self)


class ComputerSystem_RequestStateChange_ReturnCodes(RangedCodeEnum):
  Completed_with_No_Error = 0
  Method_Parameters_Checked_Transition_Started = 4096
  Access_Denied = 32769
  Invalid_state_for_this_operation = 32775


class ComputerSystem_EnabledState(RangedCodeEnum):
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
    if self == ComputerSystem_EnabledState.Enabled:
      return VirtualMachineState.RUNNING
    elif self == ComputerSystem_EnabledState.Disabled:
      return VirtualMachineState.STOPPED
    elif self == ComputerSystem_EnabledState.EnabledButOffline:
      return VirtualMachineState.SAVED
    elif self == ComputerSystem_EnabledState.Quiesce:
      return VirtualMachineState.PAUSED
    else:
      return VirtualMachineState.UNDEFINED


class ShutdownComponent_OperationalStatus(RangedCodeEnum):
  """
  For internal usage only. Msvm_ShutdownComponent.OperationalStatus property.
  """
  OK = 2
  Degraded = 3
  NonRecoverableError = 7
  NoContact = 12
  LostCommunication = 13


class ShutdownComponent_ShutdownComponent_ReturnCodes(RangedCodeEnum):
  Completed_with_No_Error = 0
  Method_Parameters_Checked_JobStarted = 4096
  Failed = 32768
  Access_Denied = 32769
  Not_Supported = 32770
  Status_is_unknown = 32771
  Timeout = 32772
  Invalid_parameter = 32773
  System_is_in_use = 32774
  Invalid_state_for_this_operation = 32775
  Incorrect_data_type = 32776
  System_is_not_available = 32777
  Out_of_memory = 32778
  File_not_found = 32779
  The_system_is_not_ready = 32780
  The_machine_is_locked_and_cannot_be_shut_down_without_the_force_option = 32781
  A_system_shutdown_is_in_progress = 32782


class VSMS_ModifySystemSettings_ReturnCode(RangedCodeEnum):
  """
  VirtualSystemManagementService ModifySystemSettings method return codes.
  """
  Completed_with_No_Error = 0
  Not_Supported = 1
  Failed = 2
  Timeout = 3
  Invalid_Parameter = 4
  Invalid_State = 5
  Incompatible_Parameters = 6
  # DMTF_Reserved = ?
  Method_Parameters_Checked_Job_Started = 4096
  Method_Reserved = (4097, 32767)
  Vendor_Specific = (32768, 65535)


class VSMS_ModifyResourceSettings_ReturnCode(RangedCodeEnum):
  """
  VirtualSystemManagementService ModifyResourceSettings method return codes.
  """
  Completed_with_No_Error = 0
  Not_Supported = 1
  Failed = 2
  Timeout = 3
  Invalid_Parameter = 4
  Invalid_State = 5
  Incompatible_Parameters = 6
  # DMTF_Reserved = ?
  Method_Parameters_Checked_Job_Started = 4096
  Method_Reserved = (4097, 32767)
  Vendor_Specific = (32768, 65535)


class VSMS_AddResourceSettings_ReturnCode(RangedCodeEnum):
  """
  VirtualSystemManagementService ModifyResourceSettings method return codes.
  """
  Completed_with_No_Error = 0
  Not_Supported = 1
  Failed = 2
  Timeout = 3
  Invalid_Parameter = 4
  # DMTF_Reserved = ?
  Method_Parameters_Checked_Job_Started = 4096
  Method_Reserved = (4097, 32767)
  Vendor_Specific = (32768, 65535)
