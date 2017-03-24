import clr
from enum import Enum
from typing import Tuple, Callable, Iterable, Union, List, Any, Sized

import collections

import time

from hvapi.clr_types import Msvm_ConcreteJob_JobState, VSMS_ModifySystemSettings_ReturnCode, RangedCodeEnum, \
  VSMS_ModifyResourceSettings_ReturnCode

clr.AddReference("System.Management")
from System.Management import ManagementScope, ObjectQuery, ManagementObjectSearcher, ManagementObject, CimType, \
  ManagementException
from System import Array, String


class CimTypeTransformer(object):
  """

  """

  @staticmethod
  def target_class(value):
    """
    Returns target class in witch given CimType can/must be transformed.

    :param value: System.Management.CimType enum item
    :return: target class
    """
    if value == CimType.String:
      return String
    if value == CimType.Reference:
      return ManagementObject
    if value == CimType.UInt32:
      return int
    raise Exception("unknown type")


class MOHTransformers(object):
  @staticmethod
  def from_reference(object_reference, parent: 'ManagementObjectHolder'):
    return ManagementObjectHolder(ManagementObject(object_reference), parent.scope_holder)


class Path(int, Enum):
  RELATED = 0
  PROPERTY = 1


class Property(int, Enum):
  ARRAY = 2
  SINGLE = 3


class Node(object):
  def __init__(
      self,
      node_type: Path,
      path_item: Union[str, Tuple],
      property_type: Tuple[Property, Callable[[Any, 'ManagementObjectHolder'], 'ManagementObjectHolder']] = None,
      include=True
  ):
    self.node_type = node_type
    if not isinstance(path_item, (list, tuple)):
      self.path_item = (path_item,)
    else:
      self.path_item = path_item
    self.property_type = None
    self.property_transformer = lambda x, y: x
    if property_type:
      self.property_type = property_type[0]
      if len(property_type) == 2:
        self.property_transformer = property_type[1]
    self.include = include


class ScopeHolder(object):
  def __init__(self, namespace=r"\\.\root\virtualization\v2"):
    self.scope = ManagementScope(namespace)

  def query(self, query) -> List['ManagementObjectHolder']:
    result = []
    query_obj = ObjectQuery(query)
    searcher = ManagementObjectSearcher(self.scope, query_obj)
    for man_object in searcher.Get():
      result.append(ManagementObjectHolder(man_object, self))
    return result

  def query_one(self, query) -> 'ManagementObjectHolder':
    result = self.query(query)
    if len(result) > 1:
      raise Exception("Got too many results for query '%s'" % query)
    if result:
      return result[0]


class JobException(Exception):
  def __init__(self, job):
    msg = "Job code:'%s' status:'%s' description:'%s'" % (job.ErrorCode, job.JobStatus, job.ErrorDescription)
    super().__init__(msg)


class InvocationException(Exception):
  pass


class ManagementObjectHolder(object):
  def __init__(self, management_object, scope_holder: ScopeHolder):
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
    return self._internal_traversal(traverse_path, self)

  def invoke(self, method_name, **kwargs):
    parameters = self.management_object.GetMethodParameters(method_name)
    for parameter in parameters.Properties:
      parameter_name = parameter.Name
      parameter_type = CimTypeTransformer.target_class(parameter.Type)

      if parameter_name not in kwargs:
        raise ValueError("Parameter '%s' not provided" % parameter_name)

      if parameter.IsArray:
        if not isinstance(kwargs[parameter_name], collections.Iterable):
          raise ValueError("Parameter '%s' must be iterable" % parameter_name)
        parameter_value = Array[parameter_type](
          [self._transform_object(item, parameter_type) for item in kwargs[parameter_name]])
      else:
        parameter_value = self._transform_object(kwargs[parameter_name], parameter_type)

      parameters.Properties[parameter_name].Value = parameter_value

    invocation_result = self.management_object.InvokeMethod(method_name, parameters, None)
    transformed_result = {}
    for _property in invocation_result.Properties:
      _property_type = CimTypeTransformer.target_class(_property.Type)
      _property_value = None
      if _property.Value is not None:
        if _property.IsArray:
          _property_value = [self._transform_object(item, _property_type) for item in _property.Value]
        else:
          _property_value = self._transform_object(_property.Value, _property_type)
      transformed_result[_property.Name] = _property_value
    return transformed_result

  def _transform_object(self, obj, expected_type=None):
    if obj is None:
      return None

    if isinstance(obj, ManagementObjectHolder):
      obj = obj.management_object

    if isinstance(obj, ManagementObject):
      if expected_type == String:
        return String(obj.GetText(2))
      raise ValueError("Object '%s' can not be transformed to '%s'" % (obj, expected_type))

    if isinstance(obj, (String, str)):
      if expected_type == ManagementObject:
        return MOHTransformers.from_reference(obj, self)

    if isinstance(obj, int):
      if expected_type == int:
        return obj

    raise Exception("Unknown object to transform: '%s'" % obj)

  @staticmethod
  def _get_node_objects(parent_object: 'ManagementObjectHolder', node: 'Node'):
    results = []
    if node.node_type == Path.PROPERTY:
      if node.include:
        val = parent_object.management_object.Properties[node.path_item[0]].Value
        if node.property_type == Property.SINGLE:
          results.append([node.property_transformer(val, parent_object)])
        elif node.property_type == Property.ARRAY:
          for val_item in val:
            results.append([node.property_transformer(val_item, parent_object)])
        else:
          raise Exception("Unknown property type")
      return results
    elif node.node_type == Path.RELATED:
      for rel_object in parent_object.management_object.GetRelated(*node.path_item):
        if not parent_object.management_object == rel_object:
          results.append(ManagementObjectHolder(rel_object, parent_object.scope_holder))
      return results
    else:
      raise Exception("Unknown path part type")

  @classmethod
  def _internal_traversal(cls, traverse_path: Union[Sized, Iterable[Node]], parent: 'ManagementObjectHolder'):
    results = []
    if len(traverse_path) == 1:
      for obj in cls._get_node_objects(parent, traverse_path[0]):
        results.append(obj)
      return results
    else:
      for obj in cls._get_node_objects(parent, traverse_path[0]):
        for child in cls._internal_traversal(traverse_path[1:], obj):
          cur_res = [obj]
          if isinstance(child, list):
            cur_res.extend(child)
          else:
            cur_res.append(child)
          results.append(cur_res)
      return results

  @staticmethod
  def _evaluate_invocation_result(result, codes_enum: RangedCodeEnum, ok_value, job_value):
    return_value = codes_enum.from_code(result['ReturnValue'])
    if return_value == job_value:
      return ConcreteJob.from_moh(result['Job']).wait()
    if return_value != ok_value:
      raise InvocationException("Failed to modify resource with code '%s'" % return_value.name)
    return return_value

  @staticmethod
  def _create_cls_from_moh(cls, cls_name, moh):
    if moh.management_object.ClassPath.ClassName != cls_name:
      raise ValueError('Given ManagementObject is not %s' % cls_name)
    return cls(moh.management_object, moh.scope_holder)


class ConcreteJob(ManagementObjectHolder):
  def wait(self):
    job_state = Msvm_ConcreteJob_JobState.from_code(self.JobState)
    while job_state not in [Msvm_ConcreteJob_JobState.Completed, Msvm_ConcreteJob_JobState.Terminated,
                            Msvm_ConcreteJob_JobState.Killed, Msvm_ConcreteJob_JobState.Exception]:
      time.sleep(.1)
    if job_state != Msvm_ConcreteJob_JobState.Completed:
      raise JobException(self)

  @classmethod
  def from_moh(cls, moh: 'ManagementObjectHolder') -> 'ConcreteJob':
    return cls._create_cls_from_moh(cls, 'Msvm_ConcreteJob', moh)


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

  @classmethod
  def from_moh(cls, moh: 'ManagementObjectHolder') -> 'VirtualSystemManagementService':
    return cls._create_cls_from_moh(cls, 'Msvm_VirtualSystemManagementService', moh)


### TESTING
# scope = ScopeHolder()

# system_service = VirtualSystemManagementService.from_holder(
#   scope.query_one('SELECT * FROM Msvm_VirtualSystemManagementService'))

# linux_machine = scope.query_one(
#   'SELECT * FROM Msvm_ComputerSystem WHERE Caption = "Virtual Machine" AND ElementName="hello"')
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
#   )
#   ,
#   # Node(Path.RELATED, "Msvm_ProcessorSettingData")
# )

# res = (linux_machine.traverse(path))[-1][-1]
# res = (linux_machine.traverse(path))[-1]
# res.oh_lol = 1
# print(res.oh_lol)
# print(res.VirtualQuantity)
# res.management_object.Properties['VirtualQuantity'].Value = 8
# modification_result = system_service.ModifySystemSettings(res)

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
