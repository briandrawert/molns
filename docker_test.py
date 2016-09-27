from MolnsLib.Docker import Docker
import tempfile
import MolnsLib.installSoftware
from MolnsLib.DockerProvider import DockerProvider

commands = MolnsLib.installSoftware.InstallSW.command_list

docker = Docker()
#
# container = docker.create_container()
#
# docker.start_container(container)
#
# print "is container running: {0}".format(docker.is_container_running(container))
#
#
# for entry in command_list:
#         if isinstance(entry, list):
#             for sub_entry in entry:
#                 ret_val, response = docker.execute_command(container, sub_entry)
#                 print "RETURN VALUE: {0}".format(ret_val)
#                 if ret_val is None or ret_val.get('ExitCode') != 0:
#                     print "ERROR"
#                     print "RESPONSE: {0}".format(response)
#                 print "__"
#                 print "__"
#
#         else:
#             ret_val, response = docker.execute_command(container, entry)
#             print "RETURN VALUE: {0}".format(ret_val)
#             if ret_val is None or ret_val.get('ExitCode') != 0:
#                 print "ERROR"
#                 print "RESPONSE: {0}".format(response)
#             print "__"
#             print "__"
def create_dockerfile(commands):
    dockerfile = '''FROM ubuntu:14.04\nRUN apt-get update\n# Set up base environment.\nRUN apt-get install -yy \ \n  software-properties-common \    \n    python-software-properties \ \n    wget \ \n  curl \ \n   git \ \n    ipython \n# Add user ubuntu.\nRUN useradd -ms /bin/bash ubuntu\nWORKDIR /home/ubuntu'''

    flag = False

    for entry in commands:
        if isinstance(entry, list):
            dockerfile += '''\n\nRUN '''
            first = True
            flag = False
            for sub_entry in entry:
                if first is True:
                    dockerfile += _preprocess(sub_entry)
                    first = False
                else:
                    dockerfile += ''' && \ \n   ''' + _preprocess(sub_entry)
        else:
            if flag is False:
                dockerfile += '''\n\nRUN '''
                flag = True
                dockerfile += _preprocess(entry)
            else:
                dockerfile += ''' && \ \n    ''' + _preprocess(entry)

    dockerfile += '''\n\nUSER ubuntu\nENV HOME /home/ubuntu'''

    return dockerfile


def _preprocess(command):
    """ Filters out any sudos in the command, prepends shell only commands with '/bin/bash -c'. """
    for shell_command in Docker.shell_commands:
        if shell_command in command:
            replace_string = "/bin/bash -c \"" + shell_command
            command = command.replace(shell_command, replace_string)
            command += "\""
    return command.replace("sudo", "")

print("Creating Dockerfile...")
dockerfile = create_dockerfile(commands)
print("---------------Dockerfile----------------")
print(dockerfile)
print("-----------------------------------------")
print("Building image...")
tmpfh = tempfile.NamedTemporaryFile()
tmpfh.write(dockerfile)
print("tmph name: " + tmpfh.name)
tmpfh.seek(0)
image_tag = docker.build_image(tmpfh)

print("Image created.")

