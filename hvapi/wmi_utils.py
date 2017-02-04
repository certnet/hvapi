import time
from enum import Enum
from typing import Tuple, Callable, Iterable

import wmi


class WmiHelper(object):
  def __init__(self, namespace=r"root\virtualization\v2", server='localhost'):
    connection = wmi.connect_server(server=server, namespace=namespace)
    self.conn = wmi.WMI(wmi=connection)
    self.management = self.conn.Msvm_VirtualSystemManagementService()[0]

  def query(self, query):
    return self.conn.query(query)

  def query_one(self, query):
    res = self.conn.query(query)
    if len(res) != 1:
      raise Exception("Wanted one instance but got %d" % len(res))
    return res[0]

  def get(self, wmi_path):
    return self.conn.get(wmi_path)


class Path(int, Enum):
  RELATED = 0
  PROPERTY = 1


class Property(int, Enum):
  ARRAY = 2
  SINGLE = 3


class Node(object):
  def __init__(self, node_type: Path, name: str, property_type: Tuple[Property, Callable] = None, include=True):
    self.node_type = node_type
    self.name = name
    self.property_type = None
    self.property_transfomer = lambda x: x
    if property_type:
      self.property_type = property_type[0]
      if len(property_type) == 2:
        self.property_transfomer = property_type[1]
    self.include = include


def _get_node_objects(parent_object, node):
  results = []
  if node.node_type == Path.PROPERTY:
    if node.include:
      val = getattr(parent_object, node.name)
      if node.property_type == Property.SINGLE:
        results.append([node.property_transfomer(val)])
      elif node.property_type == Property.ARRAY:
        for val_item in val:
          results.append([node.property_transfomer(val_item)])
      else:
        raise Exception("Unknown property type")
    return results
  elif node.node_type == Path.RELATED:
    for asobj in parent_object.associators(wmi_result_class=node.name):
      if not parent_object == asobj:
        results.append(asobj)
    return results
  else:
    raise Exception("Unknown path part type")


def management_object_traversal(_path: Iterable[Node], parent: wmi._wmi_object):
  """
  Tries to traverse over wmi objects accordingly specified path. Will return list of all possible paths. Example::

    port_to_switch_path = (
      Node(Path.RELATED, "Msvm_VirtualSystemSettingData"),
      Node(Path.RELATED, "Msvm_SyntheticEthernetPortSettingData"),
      Node(Path.RELATED, "Msvm_EthernetPortAllocationSettingData"),
      Node(Path.PROPERTY, "HostResource", (Property.ARRAY, helper.get))
    )
    result = management_object_traversal(port_to_switch_path, linux_vm)
    pprint.pprint(result)
  This will print list of lists with wmi objects of following classes: [Msvm_VirtualSystemSettingData,
  Msvm_SyntheticEthernetPortSettingData, Msvm_EthernetPortAllocationSettingData, Msvm_VirtualEthernetSwitch].

  :param _path: ``Iterable[Node]``
  :param parent: parent object that will be used as starting point
  :return:
  """
  results = []
  if len(_path) == 1:
    for obj in _get_node_objects(parent, _path[0]):
      results.append(obj)
    return results
  else:
    for obj in _get_node_objects(parent, _path[0]):
      for child in management_object_traversal(_path[1:], obj):
        cur_res = [obj]
        if isinstance(child, list):
          cur_res.extend(child)
        else:
          cur_res.append(child)
        results.append(cur_res)
    return results


def get_wmi_object_properties(obj: wmi._wmi_object):
  result = {}
  for prop in obj._properties:
    result[prop] = getattr(obj, prop)
  return result


class RangedCodeEnum(Enum):
  @classmethod
  def from_code(cls, value):
    for enum_item in list(cls):
      enum_val = enum_item.value
      if len(enum_val) == 1:
        if enum_val[0] == value:
          return enum_item
      elif enum_val[0] <= value <= enum_val[1]:
        return enum_item


class IntEnum(int, Enum):
  @classmethod
  def from_code(cls, value):
    for enum_item in list(cls):
      if enum_item.value == value:
        return enum_item


class JobStateCodes(RangedCodeEnum):
  Starting = (3,)
  Running = (4,)
  Suspended = (5,)
  Shutting_Down = (6,)
  Completed = (7,)
  Terminated = (8,)
  Killed = (9,)
  Exception = (10,)
  Service = (11,)
  DMTF_Reserved = (12, 32767)
  Vendor_Reserved = (32768, 65535)


def wait_for_wmi_job(job_path):
  job_wmi_path = job_path.replace('\\', '/')
  job = wmi.WMI(moniker=job_wmi_path)

  while JobStateCodes.from_code(job.JobState) == JobStateCodes.Running:
    time.sleep(1.)
    job = wmi.WMI(moniker=job_wmi_path)
  result_state = JobStateCodes.from_code(job.JobState)
  if result_state != JobStateCodes.Completed:
    raise Exception("Job('%s', '%s') finished with state '%s' and Error('%s', '%s', '%s')" % (
      job.Name, job.Description, result_state, job.ErrorCode, job.ErrorDescription, job.ErrorSummaryDescription))
