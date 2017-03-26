import ctypes
from ctypes import wintypes
from enum import Enum

from hvapi.disk.types import VHDException

kernel32 = ctypes.windll.kernel32
virtdisk = ctypes.windll.virtdisk

# CONSTANTS
VIRTUAL_STORAGE_TYPE_DEVICE_UNKNOWN = 0
VIRTUAL_STORAGE_TYPE_DEVICE_ISO = 1
VIRTUAL_STORAGE_TYPE_DEVICE_VHD = 2
VIRTUAL_STORAGE_TYPE_DEVICE_VHDX = 3
VIRTUAL_DISK_ACCESS_NONE = 0
VIRTUAL_DISK_ACCESS_CREATE = 0x00100000
VIRTUAL_DISK_ACCESS_GET_INFO = 0x80000
OPEN_VIRTUAL_DISK_FLAG_NO_PARENTS = 1
OPEN_VIRTUAL_DISK_VERSION_1 = 1
OPEN_VIRTUAL_DISK_VERSION_2 = 2
RESIZE_VIRTUAL_DISK_FLAG_NONE = 0
RESIZE_VIRTUAL_DISK_VERSION_1 = 1
CREATE_VIRTUAL_DISK_VERSION_2 = 2
CREATE_VHD_PARAMS_DEFAULT_BLOCK_SIZE = 0
CREATE_VIRTUAL_DISK_FLAG_NONE = 0
CREATE_VIRTUAL_DISK_FLAG_FULL_PHYSICAL_ALLOCATION = 1
MERGE_VIRTUAL_DISK_VERSION_1 = 1
MERGE_VIRTUAL_DISK_FLAG_NONE = 0x00000000
SET_VIRTUAL_DISK_INFO_PARENT_PATH = 1


# STRUCTURES, STRUCTURES INSTANCES, ETC
class GUID(ctypes.Structure):
  _fields_ = [("Data1", wintypes.DWORD),
              ("Data2", wintypes.WORD),
              ("Data3", wintypes.WORD),
              ("Data4", wintypes.BYTE * 8)]

  def __str__(self):
    return "%08X-%04X-%04X-%02X%02X-%02X%02X%02X%02X%02X%02X" % (
      self.Data1,
      self.Data2,
      self.Data3,
      ctypes.c_ubyte(self.Data4[0]).value,
      ctypes.c_ubyte(self.Data4[1]).value,
      ctypes.c_ubyte(self.Data4[2]).value,
      ctypes.c_ubyte(self.Data4[3]).value,
      ctypes.c_ubyte(self.Data4[4]).value,
      ctypes.c_ubyte(self.Data4[5]).value,
      ctypes.c_ubyte(self.Data4[6]).value,
      ctypes.c_ubyte(self.Data4[7]).value
    )

  def __repr__(self):
    return str(self)


class VIRTUAL_STORAGE_TYPE(ctypes.Structure):
  _fields_ = [
    ('DeviceId', wintypes.ULONG),
    ('VendorId', GUID)
  ]


class RESIZE_VIRTUAL_DISK_PARAMETERS(ctypes.Structure):
  _fields_ = [
    ('Version', wintypes.DWORD),
    ('NewSize', ctypes.c_ulonglong)
  ]


class OPEN_VIRTUAL_DISK_PARAMETERS_V1(ctypes.Structure):
  _fields_ = [
    ('Version', wintypes.DWORD),
    ('RWDepth', ctypes.c_ulong),
  ]


class OPEN_VIRTUAL_DISK_PARAMETERS_V2(ctypes.Structure):
  _fields_ = [
    ('Version', wintypes.DWORD),
    ('GetInfoOnly', wintypes.BOOL),
    ('ReadOnly', wintypes.BOOL),
    ('ResiliencyGuid', GUID)
  ]


class MERGE_VIRTUAL_DISK_PARAMETERS(ctypes.Structure):
  _fields_ = [
    ('Version', wintypes.DWORD),
    ('MergeDepth', ctypes.c_ulong)
  ]


class CREATE_VIRTUAL_DISK_PARAMETERS(ctypes.Structure):
  _fields_ = [
    ('Version', wintypes.DWORD),
    ('UniqueId', GUID),
    ('MaximumSize', ctypes.c_ulonglong),
    ('BlockSizeInBytes', wintypes.ULONG),
    ('SectorSizeInBytes', wintypes.ULONG),
    ('PhysicalSectorSizeInBytes', wintypes.ULONG),
    ('ParentPath', wintypes.LPCWSTR),
    ('SourcePath', wintypes.LPCWSTR),
    ('OpenFlags', wintypes.DWORD),
    ('ParentVirtualStorageType', VIRTUAL_STORAGE_TYPE),
    ('SourceVirtualStorageType', VIRTUAL_STORAGE_TYPE),
    ('ResiliencyGuid', GUID)
  ]


class SIZE(ctypes.Structure):
  _fields_ = [("VirtualSize", wintypes.ULARGE_INTEGER),
              ("PhysicalSize", wintypes.ULARGE_INTEGER),
              ("BlockSize", wintypes.ULONG),
              ("SectorSize", wintypes.ULONG)]


class PARENT_LOCATION(ctypes.Structure):
  _fields_ = [('ParentResolved', wintypes.BOOL),
              ('ParentLocationBuffer', wintypes.WCHAR * 512)]


class PHYSICAL_DISK(ctypes.Structure):
  _fields_ = [("LogicalSectorSize", wintypes.ULONG),
              ("PhysicalSectorSize", wintypes.ULONG),
              ("IsRemote", wintypes.BOOL)]


class ChangeTrackingState(ctypes.Structure):
  _fields_ = [('Enabled', wintypes.BOOL),
              ('NewerChanges', wintypes.BOOL),
              ('MostRecentId', wintypes.WCHAR * 512)]


class VHD_INFO(ctypes.Union):
  _fields_ = [("Size", SIZE),
              ("Identifier", GUID),
              ("ParentLocation", PARENT_LOCATION),
              ("ParentIdentifier", GUID),
              ("ParentTimestamp", wintypes.ULONG),
              ("VirtualStorageType", VIRTUAL_STORAGE_TYPE),
              ("ProviderSubtype", wintypes.ULONG),
              ("Is4kAligned", wintypes.BOOL),
              ("IsLoaded", wintypes.BOOL),
              ("PhysicalDisk", PHYSICAL_DISK),
              ("VhdPhysicalSectorSize", wintypes.ULONG),
              ("SmallestSafeVirtualSize", wintypes.ULARGE_INTEGER),
              ("FragmentationPercentage", wintypes.ULONG),
              ("VirtualDiskId", GUID),
              ("ChangeTrackingState", ChangeTrackingState)
              ]


class GET_VIRTUAL_DISK_INFO_PARAMETERS(ctypes.Structure):
  _fields_ = [("VERSION", wintypes.UINT),
              ("VhdInfo", VHD_INFO)]


class SET_VIRTUAL_DISK_INFO_PARAMETERS(ctypes.Structure):
  _fields_ = [
    ('Version', wintypes.DWORD),
    ('ParentFilePath', wintypes.LPCWSTR)
  ]


def create_WIN32_VIRTUAL_STORAGE_TYPE_VENDOR_MSFT():
  guid = GUID()
  guid.Data1 = 0xec984aec
  guid.Data2 = 0xa0f9
  guid.Data3 = 0x47e9
  ByteArray8 = wintypes.BYTE * 8
  guid.Data4 = ByteArray8(0x90, 0x1f, 0x71, 0x41, 0x5a, 0x66, 0x34, 0x5b)
  return guid


# METHODS
def path_to_device_id(path: str):
  """
  Maps dist path to device constants passed to VIRTUAL_STORAGE_TYPE structure.

  :param path: path do virtual disk
  :return: matched constant
  """
  if path.endswith("iso"):
    return VIRTUAL_STORAGE_TYPE_DEVICE_ISO
  if path.endswith("vhd"):
    return VIRTUAL_STORAGE_TYPE_DEVICE_VHD
  if path.endswith("vhdx"):
    return VIRTUAL_STORAGE_TYPE_DEVICE_VHDX
  raise Exception("Unknown disk extension")


def create_virtual_storage_type_structure(disk_path: str):
  vst = VIRTUAL_STORAGE_TYPE()
  vst.DeviceId = path_to_device_id(disk_path)
  vst.VendorId = WIN32_VIRTUAL_STORAGE_TYPE_VENDOR_MSFT
  return vst


WIN32_VIRTUAL_STORAGE_TYPE_VENDOR_MSFT = create_WIN32_VIRTUAL_STORAGE_TYPE_VENDOR_MSFT()


class GET_VIRTUAL_DISK_INFO_VERSION(Enum):
  GET_VIRTUAL_DISK_INFO_SIZE = 1, 'Size'
  GET_VIRTUAL_DISK_INFO_IDENTIFIER = 2, 'Identifier'
  GET_VIRTUAL_DISK_INFO_PARENT_LOCATION = 3, 'ParentLocation'
  GET_VIRTUAL_DISK_INFO_PARENT_IDENTIFIER = 4, 'ParentIdentifier'
  GET_VIRTUAL_DISK_INFO_PARENT_TIMESTAMP = 5, 'ParentTimestamp'
  GET_VIRTUAL_DISK_INFO_VIRTUAL_STORAGE_TYPE = 6, 'VirtualStorageType'
  GET_VIRTUAL_DISK_INFO_PROVIDER_SUBTYPE = 7, 'ProviderSubtype'
  GET_VIRTUAL_DISK_INFO_IS_4K_ALIGNED = 8, 'Is4kAligned'
  GET_VIRTUAL_DISK_INFO_PHYSICAL_DISK = 9, 'PhysicalDisk'
  GET_VIRTUAL_DISK_INFO_VHD_PHYSICAL_SECTOR_SIZE = 10, 'VhdPhysicalSectorSize'
  GET_VIRTUAL_DISK_INFO_SMALLEST_SAFE_VIRTUAL_SIZE = 11, 'SmallestSafeVirtualSize'
  GET_VIRTUAL_DISK_INFO_FRAGMENTATION = 12, 'FragmentationPercentage'
  GET_VIRTUAL_DISK_INFO_IS_LOADED = 13, 'IsLoaded'
  GET_VIRTUAL_DISK_INFO_VIRTUAL_DISK_ID = 14, 'VirtualDiskId'
  GET_VIRTUAL_DISK_INFO_CHANGE_TRACKING_STATE = 15, 'ChangeTrackingState'

  @property
  def int_value(self):
    return self.value[0]

  @property
  def member_name(self):
    return self.value[1]

  @classmethod
  def all_properties(cls):
    return list(cls)


def close_handle(handle):
  """
  Close winapi handle.

  :param handle:  handle to close
  """
  kernel32.CloseHandle(handle)


VIRTUAL_DISK_ACCESS_ALL = 0x003f0000
OPEN_VIRTUAL_DISK_FLAG_NONE = 0


def open_vhd(vhd_path, open_flag=OPEN_VIRTUAL_DISK_FLAG_NONE, open_access_mask=VIRTUAL_DISK_ACCESS_ALL,
             open_params=0) -> wintypes.HANDLE:
  vst = create_virtual_storage_type_structure(vhd_path)
  handle = wintypes.HANDLE()

  ret_val = virtdisk.OpenVirtualDisk(ctypes.byref(vst),
                                     ctypes.c_wchar_p(vhd_path),
                                     open_access_mask,
                                     open_flag,
                                     open_params,
                                     ctypes.byref(handle))
  if ret_val:
    raise VHDException("Error calling OpenVirtualDisk: %s" % ret_val)
  return handle


def create_vhd(new_vhd_path, src_path=None, max_internal_size=0, parent_path=None):
  vst = create_virtual_storage_type_structure(new_vhd_path)

  params = CREATE_VIRTUAL_DISK_PARAMETERS()
  params.Version = CREATE_VIRTUAL_DISK_VERSION_2
  params.UniqueId = GUID()
  params.BlockSizeInBytes = CREATE_VHD_PARAMS_DEFAULT_BLOCK_SIZE
  params.SectorSizeInBytes = 0x200
  params.PhysicalSectorSizeInBytes = 0x200
  params.OpenFlags = OPEN_VIRTUAL_DISK_FLAG_NONE
  params.ResiliencyGuid = GUID()
  params.MaximumSize = max_internal_size
  params.ParentPath = parent_path
  params.ParentVirtualStorageType = VIRTUAL_STORAGE_TYPE()

  if src_path:
    params.SourcePath = src_path
    params.SourceVirtualStorageType = VIRTUAL_STORAGE_TYPE()
    params.SourceVirtualStorageType.DeviceId = path_to_device_id(src_path)
    params.SourceVirtualStorageType.VendorId = WIN32_VIRTUAL_STORAGE_TYPE_VENDOR_MSFT

  handle = wintypes.HANDLE()
  create_virtual_disk_flag = CREATE_VIRTUAL_DISK_FLAG_NONE

  ret_val = virtdisk.CreateVirtualDisk(
    ctypes.byref(vst),
    ctypes.c_wchar_p(new_vhd_path),
    VIRTUAL_DISK_ACCESS_NONE,
    None,
    create_virtual_disk_flag,
    0,
    ctypes.byref(params),
    None,
    ctypes.byref(handle)
  )

  if ret_val:
    raise VHDException("Error calling CreateVirtualDisk: %s" % ret_val)

  return handle


def get_vhd_info(disk_path, requested_properties=GET_VIRTUAL_DISK_INFO_VERSION.all_properties()):
  result = {}

  disk_handle = open_vhd(disk_path, open_access_mask=VIRTUAL_DISK_ACCESS_GET_INFO)

  for _property in requested_properties:
    member_name, value = get_vhd_property(disk_handle, _property)
    result[member_name] = value

  close_handle(disk_handle)
  return result


def get_vhd_property(disk_handle, requested_property: GET_VIRTUAL_DISK_INFO_VERSION):
  # getting structure
  vdip = GET_VIRTUAL_DISK_INFO_PARAMETERS()
  vdip.VERSION = ctypes.c_uint(requested_property.int_value)
  vdip_size = ctypes.sizeof(vdip)
  virtdisk.GetVirtualDiskInformation.restype = wintypes.DWORD
  ret_val = virtdisk.GetVirtualDiskInformation(
    disk_handle,
    ctypes.byref(ctypes.c_ulong(vdip_size)),
    ctypes.byref(vdip),
    0
  )
  if ret_val:
    # ignoring some expected errors
    if ret_val == 50:
      pass  # ERROR_NOT_SUPPORTED
    elif ret_val == 1:
      pass  # ERROR_INVALID_FUNCTION
    elif requested_property in (GET_VIRTUAL_DISK_INFO_VERSION.GET_VIRTUAL_DISK_INFO_PARENT_LOCATION,
                                GET_VIRTUAL_DISK_INFO_VERSION.GET_VIRTUAL_DISK_INFO_PARENT_IDENTIFIER,
                                GET_VIRTUAL_DISK_INFO_VERSION.GET_VIRTUAL_DISK_INFO_PARENT_TIMESTAMP):
      # sometimes it returns some unknown stuff :)
      pass
    else:
      close_handle(disk_handle)
      raise VHDException("Error calling GetVirtualDiskInformation:%s for member:%s" % (ret_val, requested_property))

  return parse_vdip_structure(vdip, requested_property)


def parse_vdip_structure(vdip, requested_property: GET_VIRTUAL_DISK_INFO_VERSION):
  """
  Parsing GET_VIRTUAL_DISK_INFO winapi structure.

  :param vdip: GET_VIRTUAL_DISK_INFO structure
  :param requested_property: GET_VIRTUAL_DISK_INFO_VERSION value
  :return: (property_name, property_value)
  """
  return requested_property.member_name, getattr(vdip.VhdInfo, requested_property.member_name)
