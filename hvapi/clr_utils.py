import clr
import collections
import time
from enum import Enum
from typing import Tuple, Callable, Iterable, Union, List, Any, Sized

from hvapi.clr_types import Msvm_ConcreteJob_JobState, VSMS_AddResourceSettings_ReturnCode
from hvapi.clr_types import VSMS_ModifySystemSettings_ReturnCode, VSMS_ModifyResourceSettings_ReturnCode
from hvapi.common_types import RangedCodeEnum

clr.AddReference("System.Management")
from System.Management import ManagementScope, ObjectQuery, ManagementObjectSearcher, ManagementObject, CimType, \
  ManagementException, ManagementClass
from System import Array, String, Guid

# WARNING, clr_Array accepts iterable, e.g. ig you will pass string - it will be array of its chars, not array of one
# string. clr_Array[clr_String](["hello"]) equals to array with one "hello" string in it
clr_Array = Array
clr_String = String


def generate_guid(fmt="B"):
  return Guid.NewGuid().ToString(fmt)


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
    if value in (CimType.UInt32, CimType.UInt16):
      return int
    if value == CimType.DateTime:
      return String
    if value == CimType.Boolean:
      return bool
    raise Exception("unknown type")


class MOHTransformers(object):
  @staticmethod
  def from_reference(object_reference, parent: 'ManagementObjectHolder'):
    return ManagementObjectHolder(ManagementObject(object_reference), parent.scope_holder)


class Relation(int, Enum):
  RELATED = 0
  RELATIONSHIP = 1
  PROPERTY = 2


class Property(int, Enum):
  ARRAY = 2
  SINGLE = 3


class Node(object):
  """
  Represents methods of traversing for WMI object hierarchy. Each Node correspondents >=0 ManagementObjects that somehow
  related to given object. Relations can be represented as GetRelated, GetRelationships methods call results (from
  ManagementObject) or as transformed ManagementObject reference grabbed form parent object property.
  """

  def __init__(
      self,
      relation_type: Relation,
      path_args: Union[str, Tuple],
      property_data: Tuple[Property, Callable[[Any, 'ManagementObjectHolder'], 'ManagementObjectHolder']] = None,
      selector: Callable[['ManagementObjectHolder'], bool] = None
  ):
    """
    Constructs node. ``property_data`` contains from property type(array, or single property), and callable to transform
    property data to ManagementObject. ``selector`` is a callable that used to filter out unnecessary nodes, it will
    retrieve ManagementObject instance and need return True if this ManagementObject meets our requirements.

    :param relation_type: type of relation
    :param path_args: arguments to be passed to GetRelated, GetRelationships, or string for Relation.PROPERTY
    :param property_data: stuff related to Relation.PROPERTY
    :param selector: callable, that must return True if object is ok for us
    """
    self.relation_type = relation_type

    if not isinstance(path_args, (list, tuple)):
      self.path_args = (path_args,)
    else:
      self.path_args = path_args

    self.property_type = None
    self.property_transformer = lambda x, y: x
    if property_data:
      self.property_type = property_data[0]
      if len(property_data) == 2:
        self.property_transformer = property_data[1]
    self.selector = selector


VirtualSystemSettingDataNode = Node(Relation.RELATED, (
  "Msvm_VirtualSystemSettingData", "Msvm_SettingsDefineState", None, None, "SettingData", "ManagedElement", False,
  None))


def PropertySelector(property_name, expected_value):
  def _sel(obj):
    return obj.properties[property_name] == expected_value

  return _sel


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

  def cls_instance(self, class_name):
    cls = ManagementClass(str(self.scope.Path) + ":" + class_name)
    return ManagementObjectHolder(cls.CreateInstance(), self)


class JobException(Exception):
  def __init__(self, job):
    msg = "Job code:'%s' status:'%s' description:'%s'" % (
      job.properties.ErrorCode, job.properties.JobStatus, job.properties.ErrorDescription)
    super().__init__(msg)


class InvocationException(Exception):
  pass


class PropertiesHolder(object):
  def __init__(self, management_object):
    self.management_object = management_object

  def __getattribute__(self, key):
    if key != 'management_object':
      try:
        return self.management_object.Properties[key].Value
      except ManagementException as e:
        pass
    return super().__getattribute__(key)

  def __setattr__(self, key, value):
    if key != 'management_object':
      try:
        self.management_object.Properties[key].Value = value
      except ManagementException:
        pass
      except AttributeError:
        pass
    super().__setattr__(key, value)

  def __getitem__(self, item):
    return self.management_object.Properties[item].Value


class ManagementObjectHolder(object):
  def __init__(self, management_object, scope_holder: ScopeHolder):
    self.scope_holder = scope_holder
    self.management_object = management_object

  def reload(self):
    self.management_object.Get()

  @property
  def properties(self):
    return PropertiesHolder(self.management_object)

  @property
  def properties_dict(self):
    result = {}
    for _property in self.management_object.Properties:
      result[_property.Name] = _property.Value
    return result

  def traverse(self, traverse_path: Iterable[Node]) -> List[List['ManagementObjectHolder']]:
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
        array_items = [self._transform_object(item, parameter_type) for item in kwargs[parameter_name]]
        if array_items:
          parameter_value = Array[parameter_type](array_items)
        else:
          parameter_value = None
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

  def __str__(self):
    return str(self.management_object)

  def _transform_object(self, obj, expected_type=None):
    if obj is None:
      return None

    if isinstance(obj, ManagementObjectHolder):
      obj = obj.management_object

    if isinstance(obj, ManagementObject):
      if expected_type == String:
        return String(obj.GetText(2))
      if expected_type == ManagementObject:
        return obj
      raise ValueError("Object '%s' can not be transformed to '%s'" % (obj, expected_type))

    if isinstance(obj, (String, str)):
      if expected_type == ManagementObject:
        return MOHTransformers.from_reference(obj, self)

    if isinstance(obj, int):
      if expected_type == int:
        return obj

    if isinstance(obj, bool):
      if expected_type == bool:
        return obj

    if isinstance(obj, (str, String)):
      if expected_type == String:
        return String

    raise Exception("Unknown object to transform: '%s'" % obj)

  @staticmethod
  def _get_node_objects(parent_object: 'ManagementObjectHolder', node: 'Node'):
    results = []
    if node.relation_type == Relation.PROPERTY:
      val = parent_object.management_object.Properties[node.path_args[0]].Value
      if node.property_type == Property.SINGLE:
        _result = node.property_transformer(val, parent_object)
        if node.selector:
          if node.selector(_result):
            results.append(_result)
        else:
          results.append(_result)
      elif node.property_type == Property.ARRAY:
        for val_item in val:
          _result = node.property_transformer(val_item, parent_object)
          if node.selector:
            if node.selector(_result):
              results.append(_result)
          else:
            results.append(_result)
      else:
        raise Exception("Unknown property type")
      return results
    elif node.relation_type == Relation.RELATED:
      for rel_object in parent_object.management_object.GetRelated(*node.path_args):
        if not parent_object.management_object == rel_object:
          _result = ManagementObjectHolder(rel_object, parent_object.scope_holder)
          if node.selector:
            if node.selector(_result):
              results.append(_result)
          else:
            results.append(_result)
      return results
    elif node.relation_type == Relation.RELATIONSHIP:
      for rel_object in parent_object.management_object.GetRelationships(*node.path_args):
        if not parent_object.management_object == rel_object:
          _result = ManagementObjectHolder(rel_object, parent_object.scope_holder)
          if node.selector:
            if node.selector(_result):
              results.append(_result)
          else:
            results.append(_result)
      return results
    else:
      raise Exception("Unknown path part type")

  @classmethod
  def _internal_traversal(cls, traverse_path: Union[Sized, Iterable[Node]], parent: 'ManagementObjectHolder'):
    results = []
    if len(traverse_path) == 1:
      for obj in cls._get_node_objects(parent, traverse_path[0]):
        results.append([obj])
      return results
    else:
      for obj in cls._get_node_objects(parent, traverse_path[0]):
        for children in cls._internal_traversal(traverse_path[1:], obj):
          cur_res = [obj]
          cur_res.extend(children)
          results.append(cur_res)
      return results

  @staticmethod
  def _evaluate_invocation_result(result, codes_enum: RangedCodeEnum, ok_value, job_value):
    return_value = codes_enum.from_code(result['ReturnValue'])
    if return_value == job_value:
      ConcreteJob.from_moh(result['Job']).wait()
      return result
    if return_value != ok_value:
      raise InvocationException("Failed execute method with return value '%s'" % return_value.name)
    return result

  @staticmethod
  def _create_cls_from_moh(cls, cls_name, moh):
    if moh.management_object.ClassPath.ClassName != cls_name:
      raise ValueError('Given ManagementObject is not %s' % cls_name)
    return cls(moh.management_object, moh.scope_holder)


class ConcreteJob(ManagementObjectHolder):
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

  def AddResourceSettings(self, AffectedConfiguration, *args):
    out_objects = self.invoke("AddResourceSettings", AffectedConfiguration=AffectedConfiguration, ResourceSettings=args)
    return self._evaluate_invocation_result(
      out_objects,
      VSMS_AddResourceSettings_ReturnCode,
      VSMS_AddResourceSettings_ReturnCode.Completed_with_No_Error,
      VSMS_AddResourceSettings_ReturnCode.Method_Parameters_Checked_Job_Started
    )

    """ResourceSettings=[], ReferenceConfiguration=None,
    #                                                     SystemSettings
    """

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
  def from_holder(cls, moh: 'ManagementObjectHolder') -> 'VirtualSystemManagementService':
    return cls._create_cls_from_moh(cls, 'Msvm_VirtualSystemManagementService', moh)
