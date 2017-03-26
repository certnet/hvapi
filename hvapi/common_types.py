import collections
from enum import Enum


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
