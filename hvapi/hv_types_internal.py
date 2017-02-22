from enum import Enum


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
    from hvapi.hyperv import VirtualMachineState
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
