import logging
import time
import os

from collections import OrderedDict
from molns_provider import ProviderBase, ProviderException

logging.basicConfig()
logger = logging.getLogger("Docker")
logger.setLevel(logging.DEBUG)

def docker_provider_default_key_name():
    user = os.environ.get('USER') or 'USER'
    return "{0}_molns_docker_sshkey_{1}".format(user, hex(int(time.time())).replace('0x',''))


class DockerBase(ProviderBase):
    """ Abstract class for Docker. """

    SSH_KEY_EXTENSION = ".pem"
    PROVIDER_TYPE = 'Docker'


class DockerProvider(DockerBase):
    """ Provider handle for local Docker service. """

    OBJ_NAME = 'DockerProvider'

    CONFIG_VARS = OrderedDict([
        ('key_name',
            {'q': 'Docker Key Pair name', 'default': docker_provider_default_key_name(), 'ask': True}),
        ('group_name',
         {'q': 'Docker Security Group name', 'default': 'molns', 'ask': False}),
        ('ubuntu_image_name',
         {'q': 'Base Ubuntu image to use (leave blank to use ubuntu-14.04)', 'default': 'ubuntu:14.04',
          'ask': True}),
        ('molns_image_name',
         {'q': 'ID of the MOLNs image (leave empty for none)', 'default': None, 'ask': True})
    ])

    def check_ssh_key(self):
        """ Check that the SSH key is found locally and in the container.
        Returns:
            True if the key is valid, otherwise False.
        """
        ssh_key_dir = os.path.join(self.config_dir, self.name)
        logger.debug('ssh_key_dir={0}'.format(ssh_key_dir))
        if not os.path.isdir(ssh_key_dir):
            logger.debug('making ssh_key_dir={0}'.format(ssh_key_dir))
            os.makedirs(ssh_key_dir)
        ssh_key_file = os.path.join(ssh_key_dir, self.config['key_name'] + self.SSH_KEY_EXTENSION)
        if not os.path.isfile(ssh_key_file):
            logger.debug("ssh_key_file '{0}' not found".format(ssh_key_file))
            return False
        self._connect()
        return self.docker.keypair_exists(self.config['key_name'])

    def create_ssh_key(self):
        """ Create the ssh key and write the file locally. """
        self._connect()
        ssh_key_dir = os.path.join(self.config_dir, self.name)
        logger.debug('creating ssh key {0} in dir{1}'.format(self.config['key_name'], ssh_key_dir))
        self.docker.create_keypair(self.config['key_name'], ssh_key_dir)

    def check_security_group(self):
        """ Check if the security group is created. """
        self._connect()
        return self.docker.security_group_exists(self.config['group_name'])

    def create_seurity_group(self):
        """ Create the security group. """
        self._connect()
        return self.docker.create_security_group(self.config['group_name'])

    def create_molns_image(self):
        """ Create the molns image. """
        self._connect()

        # start container
        instances = self.docker.start_container(image=self.config["ubuntu_image_name"])
        instance = instances[0]

        # get login ip
        ip = instance.public_dns_name

        # install software
        try:
            logger.debug("installing software on container (ip={0}). (I am not implemented yet)".format(ip))
            # TODO Where do we store the created image?
        except Exception as e:
            logger.exception(e)
            raise ProviderException("Failed to create molns image: {0}".format(e))
        finally:
            logger.debug("stopping container {0}".format(instance))
            self.docker.stop_containers([instance])
        return None

    def check_molns_image(self):
        """ Check if the molns image exists. """
        if 'molns_image_name' in self.config and self.config['molns_image_name'] is not None and self.config[
            'molns_image_name'] != '':
            self._connect()
            return self.docker.image_exists(self.config['molns_image_name'])
        return False

    def _connect(self):
        if self.connected:
            return
        self.docker = Docker(config=self)
        self.connected = True


class Docker:
    """
    Create containers with the provided configuration.
    """

    def __init__(self, config=None):
        # TODO
        logger.debug("I am not implemented yet. The config is {0}.".format(config))

    def create_keypair(self, key_name, conf_dir):
        """
        Creates a key pair and writes it locally and on the container.
        :return: void
        """
        # TODO
        logger.debug("I am not implemented yet. The key name is {0} and conf_dir is {1}.".format(key_name, conf_dir))

    def security_group_exists(self, group_name):
        # TODO
        logger.debug("I am not implemented yet. The group name is {0}. Returning true.".format(group_name))
        return True

    def keypair_exists(self, key_name):
        # TODO
        logger.debug("I am not implemented yet. The key name is {0}. Returning true.".format(key_name))
        return True

    def create_security_group(selfself, group_name):
        # TODO
        logger.debug("I am not implemented yet. The group name is {0}.".format(group_name))

    def start_container(self, image):
        # TODO
        logger.debug("I am not implemented yet. The image is {0}.".format(image))
        return None

    def stop_containers(self, containers):
        # TODO
        logger.debug("I am not implemented yet. The containers are {0}.".format(containers))

    def image_exists(self, image):
        # TODO
        logger.debug("I am not implemented yet. The image is {0}. Returning false.".format(image))
        return False

    def get_container_status(self, container):
        # TODO
        print "hi"
        logger.debug("I am not implemented yet. The instance id is {0}. Returning None.".format(container))
        return None

    def start_docker_containers(self, image_id=None, key_name=None, group_name=None, num=1, instance_type=None):
        # TODO Create and start containers here.

        # What should be returned here? Look at EC2Provider.py, line number 485.
        logger.debug("I am not implemented yet. Returning None.")
        return None

    def resume_docker_containers(self, containers):
        num_container = len(containers)
        print "Resuming Docker container(s). This will take a minute..."
        # TODO resume containers here.

        # What should be returned?


class DockerController(DockerBase):
    """ Provider handle for a Docker controller. """

    OBJ_NAME = 'DockerController'

    CONFIG_VARS = OrderedDict([
    ])

    def _connect(self):
        if self.connected:
            return
        self.docker = Docker(config=self.provider)
        self.connected = True

    def get_container_status(self, container):
        # TODO
        logger.debug("I am not implemented yet.")

    def start_instance(self, num=1):
        """ Start or resume the controller. """
        # TODO
        logger.debug("I am not implemented yet")

    def resume_instance(self, instances):
       # TODO
       logger.debug("I am not implemented yet")

    def stop_instance(self, instances):
        # TODO
        logger.debug("I am not implemented yet")

    def terminate_instance(self, instances):
        # TODO
        logger.debug("I am not implemented yet.")


class DockerWorkerGroup(DockerController):
    """ Provider handle for Docker worker group. """

    OBJ_NAME = 'DockerWorkerGroup'

    CONFIG_VARS = OrderedDict([
        ('num_vms',
            {'q': 'Number of containers in group', 'default': '1', 'ask': True}),
    ])

    def start_container_group(self, num=1):
        """ Start worker group containers. """

        # TODO start given number of containers.
        logger.debug("I am not implemented yet.")
        # Look at EC2Provider, line 287.
        # How to store container references in the datastore?
        # What should be returned?

    def terminate_container_group(selfself, containers):
        # TODO remove given containers.
        logger.debug("I am not implemented yet.")
