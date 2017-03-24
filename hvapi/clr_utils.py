import clr
from enum import Enum
from typing import Tuple, Callable, Iterable, Union, List

import collections

import time

from hvapi.clr_types import Msvm_ConcreteJob_JobState, ModifyResourceSettings_ReturnCode

clr.AddReference("System.Management")
from System.Management import ManagementScope, ObjectQuery, ManagementObjectSearcher, ManagementObject, CimType, \
  ManagementException
from System import Array, String


def class_from_CimType_value(value):
  if value == CimType.String:
    return String
  raise Exception("unknown type")


class Path(int, Enum):
  RELATED = 0
  PROPERTY = 1


class Property(int, Enum):
  ARRAY = 2
  SINGLE = 3


class Node(object):
  def __init__(self, node_type: Path, path_item: Union[str, Tuple], property_type: Tuple[Property, Callable] = None,
               include=True):
    self.node_type = node_type
    if not isinstance(path_item, (list, tuple)):
      self.path_item = (path_item,)
    else:
      self.path_item = path_item
    self.property_type = None
    self.property_transformer = lambda x: x
    if property_type:
      self.property_type = property_type[0]
      if len(property_type) == 2:
        self.property_transformer = property_type[1]
    self.include = include


def _ManagementObject_from_reference(object_reference, scope_holder: 'ScopeHolder'):
  return ManagementObjectHolder(scope_holder, ManagementObject(object_reference))


def _get_node_objects(parent_object, node, scope_holder: 'ScopeHolder'):
  results = []
  if node.node_type == Path.PROPERTY:
    if node.include:
      val = parent_object.management_object.Properties[node.path_item[0]].Value
      if node.property_type == Property.SINGLE:
        results.append([node.property_transformer(val, scope_holder)])
      elif node.property_type == Property.ARRAY:
        for val_item in val:
          results.append([node.property_transformer(val_item, scope_holder)])
      else:
        raise Exception("Unknown property type")
    return results
  elif node.node_type == Path.RELATED:
    for rel_object in parent_object.management_object.GetRelated(*node.path_item):
      if not parent_object.management_object == rel_object:
        results.append(ManagementObjectHolder(scope_holder, rel_object))
    return results
  else:
    raise Exception("Unknown path part type")


def _ManagementObjectHolder_traversal(
    traverse_path: Iterable[Node],
    parent: 'ManagementObjectHolder',
    scope_holder: 'ScopeHolder'):
  results = []
  if len(traverse_path) == 1:
    for obj in _get_node_objects(parent, traverse_path[0], scope_holder):
      results.append(obj)
    return results
  else:
    for obj in _get_node_objects(parent, traverse_path[0], scope_holder):
      for child in _ManagementObjectHolder_traversal(traverse_path[1:], obj, scope_holder):
        cur_res = [obj]
        if isinstance(child, list):
          cur_res.extend(child)
        else:
          cur_res.append(child)
        results.append(cur_res)
    return results


class ScopeHolder(object):
  def __init__(self, namespace=r"\\.\root\virtualization\v2"):
    self.scope = ManagementScope(namespace)

  def query(self, query) -> List['ManagementObjectHolder']:
    result = []
    query_obj = ObjectQuery(query)
    searcher = ManagementObjectSearcher(self.scope, query_obj)
    for man_object in searcher.Get():
      result.append(ManagementObjectHolder(self, man_object))
    return result

  def query_one(self, query) -> 'ManagementObjectHolder':
    result = self.query(query)
    if len(result) > 1:
      raise Exception("Got too many results for query '%s'" % query)
    if result:
      return result[0]


class JobException(Exception):
  def __init__(self, job):
    props = job.properties
    msg = "Job code:'%s' status:'%s' description:'%s'" % (
      props['ErrorCode'], props['JobStatus'], props['ErrorDescription'])
    super().__init__(msg)


class ModificationException(Exception): pass


class ManagementObjectHolder(object):
  def __init__(self, scope_holder: ScopeHolder, management_object):
    self.scope_holder = scope_holder
    self.management_object = management_object

  def __getattribute__(self, key):
    if key not in ['management_object', 'scope_holder']:
      try:
        return self.management_object.Properties[key].Value
      except ManagementException:
        pass
      except AttributeError:
        pass
    return super().__getattribute__(key)

  def __setattr__(self, key, value):
    if key not in ['management_object', 'scope_holder']:
      try:
        self.management_object.Properties[key].Value = value
      except ManagementException:
        pass
      except AttributeError:
        pass
    super().__setattr__(key, value)

  @property
  def properties(self):
    result = {}
    for _property in self.management_object.Properties:
      result[_property.Name] = _property.Value
    return result

  def traverse(self, traverse_path: Iterable[Node]):
    return _ManagementObjectHolder_traversal(traverse_path, self, self.scope_holder)

  def invoke(self, method_name, **kwargs):
    def _transform_object(obj, expected_type=None):
      if isinstance(obj, ManagementObjectHolder):
        if expected_type == String:
          return String(obj.management_object.GetText(2))
        raise ValueError("Object '%s' can not be transformed to '%s'" % (obj, expected_type))
      if isinstance(obj, ManagementObject):
        if expected_type == String:
          return String(obj.GetText(2))
        raise ValueError("Object '%s' can not be transformed to '%s'" % (obj, expected_type))
      raise Exception("Unknown object to transform: '%s'" % obj)

    parameters = self.management_object.GetMethodParameters(method_name)
    for parameter in parameters.Properties:
      parameter_name = parameter.Name
      parameter_type = class_from_CimType_value(parameter.Type)

      if parameter_name not in kwargs:
        raise ValueError("Parameter '%s' not provided" % parameter_name)

      if parameter.IsArray:
        if not isinstance(kwargs[parameter_name], collections.Iterable):
          raise ValueError("Parameter '%s' must be iterable" % parameter_name)
        parameter_value = Array[parameter_type](
          [_transform_object(item, parameter_type) for item in kwargs[parameter_name]])
      else:
        parameter_value = _transform_object(kwargs[parameter_name], parameter_type)

      parameters.Properties[parameter_name].Value = parameter_value

    return self.management_object.InvokeMethod(method_name, parameters, None)

  def wait_for_job(self, reference_or_job_object):
    if isinstance(reference_or_job_object, (str, String)):
      job_object = _ManagementObject_from_reference(reference_or_job_object, self.scope_holder)
    elif isinstance(reference_or_job_object, ManagementObject):
      job_object = ManagementObjectHolder(self.scope_holder, reference_or_job_object)
    elif isinstance(reference_or_job_object, ManagementObjectHolder):
      job_object = reference_or_job_object
    else:
      raise ValueError("Not transformable object")
    if "job" not in job_object.management_object.ClassPath.ClassName.lower():
      raise ValueError("This is not job object")

    job_state = Msvm_ConcreteJob_JobState.from_code(job_object.properties["JobState"])
    while job_state not in [Msvm_ConcreteJob_JobState.Completed, Msvm_ConcreteJob_JobState.Terminated,
                            Msvm_ConcreteJob_JobState.Killed, Msvm_ConcreteJob_JobState.Exception]:
      time.sleep(1)
    if job_state != Msvm_ConcreteJob_JobState.Completed:
      raise JobException(job_object)


class VirtualSystemManagementService(ManagementObjectHolder):
  def ModifyResourceSettings(self, *args):
    out_objects = self.invoke("ModifyResourceSettings", ResourceSettings=args)
    return_value = ModifyResourceSettings_ReturnCode.from_code(out_objects.Properties['ReturnValue'].Value)
    if return_value == ModifyResourceSettings_ReturnCode.Method_Parameters_Checked_Job_Started:
      return self.wait_for_job(out_objects.Properties['Job'].Value)
    if return_value != ModifyResourceSettings_ReturnCode.Completed_with_No_Error:
      raise ModificationException("Failed to modify resource with code '%s'" % return_value.name)
    return return_value

  @classmethod
  def from_holder(cls, moh: 'ManagementObjectHolder'):
    if moh.management_object.ClassPath.ClassName != 'Msvm_VirtualSystemManagementService':
      raise ValueError('Given ManagementObject is not Msvm_VirtualSystemManagementService')
    return cls(moh.scope_holder, moh.management_object)


### TESTING
scope = ScopeHolder()

system_service = VirtualSystemManagementService.from_holder(
  scope.query_one('SELECT * FROM Msvm_VirtualSystemManagementService'))

linux_machine = scope.query_one(
  'SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine" AND ElementName="hello"')
path = (
  Node(
    Path.RELATED,
    (
      "Msvm_VirtualSystemSettingData",
      "Msvm_SettingsDefineState",
      None,
      None,
      "SettingData",
      "ManagedElement",
      False,
      None
    )
  ),
  Node(Path.RELATED, "Msvm_ProcessorSettingData")
)

res = (linux_machine.traverse(path))[-1][-1]
res.oh_lol = 1
print(res.oh_lol)
print(res.VirtualQuantity)
res.management_object.Properties['VirtualQuantity'].Value = 8
modification_result = system_service.ModifyResourceSettings(res)

pass
# in_props = system_service.management_object.GetMethodParameters("ModifySystemSettings")
# in_props.Properties["SystemSettings"].Value = .management_object.GetText(2)
# out_params = system_service.management_object.InvokeMethod(, in_props, None)
pass
# manScope = ManagementScope(r"\\.\root\virtualization\v2")
# queryObj = ObjectQuery('SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine" AND ElementName="linux"')
# vmSearcher = ManagementObjectSearcher(manScope, queryObj)
# vmCollection = vmSearcher.Get()
#
# path = (
#   Node(
#     Path.RELATED,
#     (
#       "Msvm_VirtualSystemSettingData",
#       "Msvm_SettingsDefineState",
#       None,
#       None,
#       "SettingData",
#       "ManagedElement",
#       False,
#       None
#     )
#   ),
#   Node(Path.RELATED, "Msvm_SyntheticEthernetPortSettingData"),
#   Node(Path.RELATED, "Msvm_EthernetPortAllocationSettingData"),
#   Node(Path.PROPERTY, "HostResource", (Property.ARRAY, ManagementObject_from_path))
# )
# for vm in vmCollection:
#   # res = management_object_traversal(path, vm)
#   res = ManagementObjectHolder(manScope, vm).traverse(path)
#   print()
# // define the information we want to query - in this case, just grab all properties of the object
# ObjectQuery queryObj = new ObjectQuery("SELECT * FROM Msvm_ComputerSystem");
#
# // connect and set up our search
# ManagementObjectSearcher vmSearcher = new ManagementObjectSearcher(manScope, queryObj);
# ManagementObjectCollection vmCollection = vmSearcher.Get();
#
# // loop through the machines
# foreach (ManagementObject vm in vmCollection)
# {
#     // display VM details
#     Console.WriteLine("\nName: {0}\nStatus: {1}\nDescription: {2}\n",
#                         vm["ElementName"].ToString(),
#                         vm["EnabledState"].ToString(),
#                         vm["Description"].ToString());
# }
