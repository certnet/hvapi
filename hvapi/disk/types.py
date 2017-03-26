from hvapi.common_types import RangedCodeEnum


class VHDException(Exception):
  pass


class ProviderSubtype(RangedCodeEnum):
  FIXED = 2
  DYNAMIC = 3
  DIFFERENCING = 4


class VirtualStorageType(RangedCodeEnum):
  UNKNOWN = 0
  ISO = 1
  VHD = 2
  VHDX = 3
