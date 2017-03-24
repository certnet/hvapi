from enum import Enum

import collections


class RangedCodeEnum(Enum):
  @classmethod
  def from_code(cls, value):
    for enum_item in list(cls):
      enum_val = enum_item.value
      if isinstance(enum_val, collections.Iterable):
        if len(enum_val) == 1:
          if enum_val[0] == value:
            return enum_item
        elif enum_val[0] <= value <= enum_val[1]:
          return enum_item
      elif enum_val == value:
        return enum_item


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


class ModifyResourceSettings_ReturnCode(RangedCodeEnum):
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
