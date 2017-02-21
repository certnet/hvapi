import base64
import subprocess


def exec_powershell_input(input_script):
  """
  Executes powershell script in interactive session. Just like you typed it manually. With all of that output, including
  commands you typed.

  :param input_script: script, that will be passed to interactive powershell session.
  :return: out, err, exitCode
  """
  input_script += "\n"
  input_script += "exit\n"
  process = subprocess.Popen(["powershell.exe"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
  _out, _err = process.communicate(input_script.encode())
  return _out.decode(), _err.decode(), process.returncode


def exec_powershell(command: str):
  """
  Executes inline command. Will contain only command output.

  :param command: command to execute
  :return: out, err, exitCode
  """
  encoded_command = base64.b64encode(command.encode('UTF-16LE')).decode()
  process = subprocess.Popen(["powershell.exe", "-WindowStyle", "HIDDEN", "-EncodedCommand", encoded_command],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
  _out, _err = process.communicate()
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


def exec_powershell_checked(command: str, expected_code=0) -> str:
  out, err, code = exec_powershell(command)
  if code != expected_code:
    raise Exception("Failed to execute ps:\n%s\nwith code '%s'.\nstdout:\n%s\nstderr:\n%s"
                    % (command, code, out, err))
  return out
