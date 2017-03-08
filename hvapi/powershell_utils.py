"""
The MIT License

Copyright (c) 2017 Eugene Chekanskiy, echekanskiy@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
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
