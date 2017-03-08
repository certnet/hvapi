import asyncio
import base64


class PowershellException(Exception):
  pass


async def exec_powershell(command: str):
  """
  Executes inline command. Will contain only command output.

  :param command: command to execute
  :return: out, err, exitCode
  """
  encoded_command = base64.b64encode(command.encode('UTF-16LE')).decode()
  process = await asyncio.create_subprocess_exec(
    "powershell.exe", "-WindowStyle", "HIDDEN", "-EncodedCommand", encoded_command,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE)
  _out, _err = await process.communicate()
  return _out.decode(), _err.decode(), process.returncode


def parse_properties(text: str):
  def split_properties(lines):
    property_lines = []
    cur_line = []
    for line in lines:
      if not line.startswith(" ") and ":" in line:
        if cur_line:
          property_lines.append(cur_line)
        cur_line = [line]
      elif line.startswith(" ") and cur_line:
        cur_line.append(line)
    return property_lines

  result = {}

  for prop_line in split_properties(text.splitlines()):
    strip_len = prop_line[0].find(":") + 2
    prop_name = prop_line[0].split(":")[0].strip()
    prop_value = prop_line[0][strip_len:]
    for line in prop_line[1:]:
      prop_value += line[strip_len:]

    result[prop_name] = prop_value
  return result


async def exec_powershell_checked(command: str, expected_code=0) -> str:
  out, err, code = await exec_powershell(command)
  if code != expected_code:
    raise PowershellException("Failed to execute ps:\n%s\nwith code '%s'.\nstdout:\n%s\nstderr:\n%s"
                              % (command, code, out, err))
  return out


async def parse_select_object_output(cmd, delimiter):
  """
  Parse output of Select-Object function. Script must delimit different items with ``delimiter``.

  :param cmd: command to execute
  :param delimiter: items delimiter
  :return: list of object properties
  """
  out = await exec_powershell_checked(cmd)
  machine_properties_list = [res.strip() for res in out.split(delimiter) if res.strip()]
  result = []
  for machine_properties_str in machine_properties_list:
    machine_properties = parse_properties(machine_properties_str)
    result.append(machine_properties)
  return result
