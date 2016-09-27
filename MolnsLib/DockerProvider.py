import Constants
import logging
import time
import os
import Docker
import installSoftware
import tempfile
from DockerSSH import DockerSSH
from collections import OrderedDict
from molns_provider import ProviderBase, ProviderException


def docker_provider_default_key_name():
    user = os.environ.get('USER') or 'USER'
    return "{0}_molns_docker_sshkey_{1}".format(user, hex(int(time.time())).replace('0x', ''))


class DockerBase(ProviderBase):
    """ Base class for Docker. """

    SSH_KEY_EXTENSION = ".pem"
    PROVIDER_TYPE = 'Docker'

    def __init__(self, name, config=None, config_dir=None, **kwargs):
        ProviderBase.__init__(self, name, config, config_dir, **kwargs)
        self.docker = Docker.Docker()
        self.ssh = DockerSSH(self.docker)

    def _get_container_status(self, container_id):
        self.docker.container_status(container_id)

    def start_instance(self, num=1):
        """ Start given number (or 1) containers. """
        started_containers = []
        for i in range(num):
            container_id = self.docker.create_container(self.provider.config["molns_image_name"])
            stored_container = self.datastore.get_instance(provider_instance_identifier=container_id,
                                                           ip_address=self.docker.get_container_ip_address(container_id)
                                                           , provider_id=self.provider.id, controller_id=self.id)
            started_containers.append(stored_container)
        if num == 1:
            return started_containers[0]
        return started_containers

    def resume_instance(self, instances):
        instance_ids = []
        if isinstance(instances, list):
            for instance in instances:
                instance_ids.append(instance.provider_instance_identifier)
        else:
            instance_ids.append(instances.provider_instance_identifier)
        self.docker.start_containers(instance_ids)

    def stop_instance(self, instances):
        instance_ids = []
        if isinstance(instances, list):
            for instance in instances:
                instance_ids.append(instance.provider_instance_identifier)
        else:
            instance_ids.append(instances.provider_instance_identifier)
        self.docker.stop_containers(instance_ids)

    def terminate_instance(self, instances):
        instance_ids = []
        if isinstance(instances, list):
            for instance in instances:
                instance_ids.append(instance.provider_instance_identifier)
        else:
            instance_ids.append(instances.provider_instance_identifier)
        self.docker.terminate_containers(instance_ids)

    def exec_command(self, container_id, command):
        self.docker.execute_command(container_id, command)


class DockerProvider(DockerBase):
    """ Provider handle for local Docker based service. """

    OBJ_NAME = 'DockerProvider'

    CONFIG_VARS = OrderedDict([
        ('ubuntu_image_name',
         {'q': 'Base Ubuntu image to use', 'default': Constants.Constants.DOCKER_DEFAULT_IMAGE,
          'ask': True}),
        ('molns_image_name',
         {'q': 'Local MOLNs image ID to use', 'default': '', 'ask': True}),
        ('key_name',
         {'q': 'Docker Key Pair name', 'default': "docker-default", 'ask': False}),  # Unused.
        ('group_name',
         {'q': 'Docker Security Group name', 'default': 'molns', 'ask': False}),  # Unused.
        ('login_username',
         {'default': 'ubuntu', 'ask': False})  # Unused.
    ])

    def get_config_credentials(self):
        return None

    @staticmethod
    def __get_new_dockerfile_name():
        import uuid
        filename = Constants.Constants.DOCKERFILE_NAME + str(uuid.uuid4())
        return filename

    def check_ssh_key(self):
        """ Returns true. (Implementation does not use SSH.) """
        # print "reached check_ssh_key"
        return True

    def create_ssh_key(self):
        """ Returns true.  """
        # print "reached create_ssh_key"
        ssh_key_dir = os.path.join(self.config_dir, self.name)
        fp = open(ssh_key_dir, 'w')
        fp.write("This is a dummy key.")
        fp.close()
        os.chmod(ssh_key_dir, 0o600)

    def check_security_group(self):
        """ Returns true. (Implementation does not use SSH.) """
        return True

    def create_seurity_group(self):
        """ Returns true. (Implementation does not use SSH.) """
        return True

    def create_molns_image(self):
        """ Create a molns image, save it on localhost and return ID of created image. """
        # create Dockerfile and build container.
        try:
            print("Creating Dockerfile...")
            dockerfile = self._create_dockerfile(installSoftware.InstallSW.get_command_list())
            image_id = self.docker.build_image(dockerfile)
            # print("Image created.")
            return image_id
        except Exception as e:
            logging.exception(e)
            raise ProviderException("Failed to create molns image: {0}".format(e))

    def check_molns_image(self):
        """ Check if the molns image exists. """
        if 'molns_image_name' in self.config and self.config['molns_image_name'] is not None and self.config[
            'molns_image_name'] != '':
            return self.docker.image_exists(self.config['molns_image_name'])
        return False

    def _create_dockerfile(self, commands):
        """ Create Dockerfile from given commands. """
        import pwd

        user_id = pwd.getpwnam(os.environ['SUDO_USER']).pw_uid
        dockerfile = '''FROM ubuntu:14.04\nRUN apt-get update\n\n# Add user ubuntu.\nRUN useradd -u {0} -ms /bin/bash ubuntu\n
         # Set up base environment.\nRUN apt-get install -yy \ \n    software-properties-common \
         \n    python-software-properties \ \n    wget \ \n    curl \ \n   git \ \n    ipython \ \n    sudo \
         \n    screen \ \n    iptables \nRUN echo "ubuntu ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
         \nWORKDIR /home/ubuntu\n'''.format(user_id)

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

        dockerfile += '''\n\nUSER ubuntu\nENV HOME /home/ubuntu\nVOLUME /home/ubuntu'''

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

    def get_instance_status(self, instance):
        return self.docker.container_status(instance.provider_instance_identifier)


class DockerWorkerGroup(DockerController):
    """ Provider handle for Docker worker group. """

    OBJ_NAME = 'DockerWorkerGroup'

    CONFIG_VARS = OrderedDict([
        ('num_vms',
         {'q': 'Number of containers in group', 'default': '1', 'ask': True}),
    ])
