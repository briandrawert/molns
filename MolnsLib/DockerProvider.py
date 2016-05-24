import Constants
import logging
import time
import os
import Docker
import installSoftware
import tempfile

from collections import OrderedDict
from molns_provider import ProviderBase, ProviderException


def docker_provider_default_key_name():
    user = os.environ.get('USER') or 'USER'
    return "{0}_molns_docker_sshkey_{1}".format(user, hex(int(time.time())).replace('0x', ''))


class DockerBase(ProviderBase):
    """ Abstract class for Docker. """

    SSH_KEY_EXTENSION = ".pem"
    PROVIDER_TYPE = 'Docker'


class DockerProvider(DockerBase):
    """ Provider handle for local Docker based service. """

    OBJ_NAME = 'DockerProvider'

    CONFIG_VARS = OrderedDict([
        ('ubuntu_image_name',
         {'q': 'Base Ubuntu image to use', 'default': Constants.Constants.DOCKER_DEFAULT_IMAGE,
          'ask': True}),
        ('molns_image_name',
         {'q': 'Local MOLNs image name to use', 'default': '', 'ask': True}),
        ('key_name',
         {'q': 'Docker Key Pair name', 'default': "docker-default", 'ask': False}),  # Unused.
        ('group_name',
         {'q': 'Docker Security Group name', 'default': 'molns', 'ask': True})  # Unused.
    ])

    @staticmethod
    def __get_new_dockerfile_name():
        import uuid
        filename = Constants.Constants.DOCKERFILE_NAME + str(uuid.uuid4())
        return filename

    def _connect(self):
        if self.connected:
            return
        self.docker = Docker.Docker()
        self.connected = True

    def check_ssh_key(self):
        """ Returns true. (Implementation does not use SSH.) """
        return True

    def create_ssh_key(self):
        """ Returns true. (Implementation does not use SSH.) """
        return True

    def check_security_group(self):
        """ Returns true. (Implementation does not use SSH.) """
        return True

    def create_seurity_group(self):
        """ Returns true. (Implementation does not use SSH.) """
        return True

    def create_molns_image(self):
        """ Create a molns image, save it on localhost and return ID of created image. """
        self._connect()
        # create Dockerfile and build container.
        try:
            print("Creating Dockerfile...")
            dockerfile = self._create_dockerfile(installSoftware.InstallSW.get_command_list())
            image_id = self.docker.build_image(dockerfile)
            print("Image created.")
            return image_id
        except Exception as e:
            logging.exception(e)
            raise ProviderException("Failed to create molns image: {0}".format(e))

    def check_molns_image(self):
        """ Check if the molns image exists. """
        if 'molns_image_name' in self.config and self.config['molns_image_name'] is not None and self.config[
            'molns_image_name'] != '':
            self._connect()
            return self.docker.image_exists(self.config['molns_image_name'])
        return False

    def _create_dockerfile(self, commands):
        """ Create Dockerfile from given commands. """
        dockerfile = '''FROM ubuntu:14.04\nRUN apt-get update\n# Set up base environment.\nRUN apt-get install -yy \ \n
         software-properties-common \ \n    python-software-properties \ \n    wget \ \n    curl \ \n git \ \n
         ipython \n# Add user ubuntu.\nRUN useradd -ms /bin/bash ubuntu\nWORKDIR /home/ubuntu\n'''

        flag = False

        for entry in commands:
            if isinstance(entry, list):
                dockerfile += '''\n\nRUN '''
                first = True
                flag = False
                for sub_entry in entry:
                    if first is True:
                        dockerfile += self._preprocess(sub_entry)
                        first = False
                    else:
                        dockerfile += ''' && \ \n   ''' + self._preprocess(sub_entry)
            else:
                if flag is False:
                    dockerfile += '''\n\nRUN '''
                    flag = True
                    dockerfile += self._preprocess(entry)
                else:
                    dockerfile += ''' && \ \n    ''' + self._preprocess(entry)

        dockerfile += '''\n\nUSER ubuntu\nENV HOME /home/ubuntu'''

        dockerfile_file = DockerProvider.__get_new_dockerfile_name()
        with open(dockerfile_file, 'w') as Dockerfile:
            Dockerfile.write(dockerfile)
        print("Using as dockerfile : " + dockerfile_file)
        named_dockerfile = tempfile.NamedTemporaryFile()
        named_dockerfile.write(dockerfile)
        named_dockerfile.seek(0)

        return named_dockerfile

    def _preprocess(self, command):
        """ Filters out any sudos in the command, prepends "shell only" commands with '/bin/bash -c'. """
        for shell_command in Docker.Docker.shell_commands:
            if shell_command in command:
                replace_string = "/bin/bash -c \"" + shell_command
                command = command.replace(shell_command, replace_string)
                command += "\""
        return command.replace("sudo", "")


class DockerController(DockerBase):
    """ Provider handle for a Docker controller. """

    OBJ_NAME = 'DockerController'

    CONFIG_VARS = OrderedDict([
    ])

    def _connect(self):
        if self.connected:
            return
        self.docker = Docker.Docker()
        self.connected = True

    def get_container_status(self, container_id):
        self._connect()
        self.docker.container_status(container_id)

    def start_instance(self, num=1):
        """ Start or resume the controller. """
        self._connect()
        for i in range(num):
            self.docker.create_container(Constants.Constants.DOCKER_DEFAULT_IMAGE)  # TODO this needs to be MOLNs image.

    def resume_instance(self, instance_ids):
        self._connect()
        self.docker.start_containers(instance_ids)

    def stop_instance(self, instance_ids):
        self._connect()
        self.docker.stop_containers(instance_ids)

    def terminate_instance(self, instance_ids):
        self._connect()
        self.docker.terminate_containers(instance_ids)


class DockerWorkerGroup(DockerController):
    """ Provider handle for Docker worker group. """

    OBJ_NAME = 'DockerWorkerGroup'

    CONFIG_VARS = OrderedDict([
        ('num_vms',
         {'q': 'Number of containers in group', 'default': '1', 'ask': True}),
    ])

    def start_container_group(self, num=1):
        """ Starts worker group containers. """
        # TODO

    def terminate_container_group(self, containers):
        """ Terminates container group. """
        # TODO
