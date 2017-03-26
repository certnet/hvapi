from hvapi.disk.internal import open_vhd, get_vhd_info, GUID, create_vhd, close_handle
from hvapi.disk.types import ProviderSubtype, VirtualStorageType, VHDException


def transform_property(member_name, value):
  """
  Transforms underlying structures and types from GET_VIRTUAL_DISK_INFO to something human-readable.

  :param member_name:
  :param value:
  :return:
  """
  if member_name == 'ProviderSubtype':
    return ProviderSubtype.from_code(value)
  elif member_name == 'VirtualStorageType':
    return VirtualStorageType.from_code(value.DeviceId)
  elif member_name in ('IsLoaded', 'Enabled', 'IsRemote', 'ParentResolved', 'Is4kAligned', 'NewerChanges'):
    return bool(value)
  elif isinstance(value, GUID):
    return str(value)
  elif hasattr(value, "_fields_"):
    result = {}
    for field_name, _ in value._fields_:
      result[field_name] = transform_property(field_name, getattr(value, field_name))
    return result
  return value


class VHDDisk(object):
  def __init__(self, disk_path):
    self.disk_path = disk_path
    close_handle(open_vhd(self.disk_path))

  @property
  def properties(self):
    return {name: transform_property(name, value) for name, value in get_vhd_info(self.disk_path).items()}

  def clone(self, clone_path, differencing=True):
    """
    Creates clone of current vhd disk.

    :param clone_path: path where cloned disk will be stored
    :param differencing: indicates if disk must be thin-copy
    :return: resulting VHDDisk
    """
    if differencing:
      close_handle(create_vhd(clone_path, parent_path=self.disk_path))
    else:
      close_handle(create_vhd(clone_path, src_path=self.disk_path))
    return VHDDisk(clone_path)


# _create_vhd(r"F:\hyper-v-disks\centos6.8-clone2.vhdx", parent_path=r"F:\hyper-v-disks\centos6.8.vhdx")
# res = open_vhd()
# disk = VHDDisk("F:/hyper-v-disks/New Virtual Hard Disk - Copy.vhdx")
# print(disk.properties)
# clone_of_clone = disk.clone("F:/hyper-v-disks/helloworld.vhdx", differencing=False)
# print(clone_of_clone.properties)
""
"""
guid to string
sprintf(szGuid, "{}", guid.Data1, guid.Data2, guid.Data3, guid.Data4[0], guid.Data4[1], guid.Data4[2], guid.Data4[3], guid.Data4[4], guid.Data4[5], guid.Data4[6], guid.Data4[7]);
"""
