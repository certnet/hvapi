import time

from hvapi.clr.types import Msvm_ConcreteJob_JobState, VSMS_ModifyResourceSettings_ReturnCode, \
  VSMS_ModifySystemSettings_ReturnCode, VSMS_AddResourceSettings_ReturnCode, \
  MIMS_GetVirtualHardDiskSettingData_ReturnCode
from hvapi.clr.base import ManagementObjectHolder, JobException


class JobWrapper(ManagementObjectHolder):
  def wait(self):
    job_state = Msvm_ConcreteJob_JobState.from_code(self.properties['JobState'])
    while job_state not in [Msvm_ConcreteJob_JobState.Completed, Msvm_ConcreteJob_JobState.Terminated,
                            Msvm_ConcreteJob_JobState.Killed, Msvm_ConcreteJob_JobState.Exception]:
      job_state = Msvm_ConcreteJob_JobState.from_code(self.properties['JobState'])
      self.reload()
      time.sleep(.1)
    if job_state != Msvm_ConcreteJob_JobState.Completed:
      raise JobException(self)

  @classmethod
  def from_moh(cls, moh: 'ManagementObjectHolder') -> 'JobWrapper':
    return cls._create_cls_from_moh(cls, ('Msvm_ConcreteJob', 'Msvm_StorageJob'), moh)


class VirtualSystemManagementService(ManagementObjectHolder):
  def ModifyResourceSettings(self, *args):
    out_objects = self.invoke("ModifyResourceSettings", ResourceSettings=args)
    return self._evaluate_invocation_result(
      out_objects,
      VSMS_ModifyResourceSettings_ReturnCode,
      VSMS_ModifyResourceSettings_ReturnCode.Completed_with_No_Error,
      VSMS_ModifyResourceSettings_ReturnCode.Method_Parameters_Checked_Job_Started
    )

  def ModifySystemSettings(self, SystemSettings):
    out_objects = self.invoke("ModifySystemSettings", SystemSettings=SystemSettings)
    return self._evaluate_invocation_result(
      out_objects,
      VSMS_ModifySystemSettings_ReturnCode,
      VSMS_ModifySystemSettings_ReturnCode.Completed_with_No_Error,
      VSMS_ModifySystemSettings_ReturnCode.Method_Parameters_Checked_Job_Started
    )

  def AddResourceSettings(self, AffectedConfiguration, *args):
    out_objects = self.invoke("AddResourceSettings", AffectedConfiguration=AffectedConfiguration, ResourceSettings=args)
    return self._evaluate_invocation_result(
      out_objects,
      VSMS_AddResourceSettings_ReturnCode,
      VSMS_AddResourceSettings_ReturnCode.Completed_with_No_Error,
      VSMS_AddResourceSettings_ReturnCode.Method_Parameters_Checked_Job_Started
    )

  def DefineSystem(self, SystemSettings, ResourceSettings=[], ReferenceConfiguration=None):
    out_objects = self.invoke("DefineSystem", SystemSettings=SystemSettings, ResourceSettings=ResourceSettings,
                              ReferenceConfiguration=ReferenceConfiguration)
    return self._evaluate_invocation_result(
      out_objects,
      VSMS_AddResourceSettings_ReturnCode,
      VSMS_AddResourceSettings_ReturnCode.Completed_with_No_Error,
      VSMS_AddResourceSettings_ReturnCode.Method_Parameters_Checked_Job_Started
    )

  @classmethod
  def from_moh(cls, moh: 'ManagementObjectHolder') -> 'VirtualSystemManagementService':
    return cls._create_cls_from_moh(cls, 'Msvm_VirtualSystemManagementService', moh)
