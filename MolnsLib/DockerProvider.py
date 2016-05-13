import Constants
import logging
import time
import os
import Docker
import installSoftware

from collections import OrderedDict
from molns_provider import ProviderBase, ProviderException

logging.basicConfig()
logger = logging.getLogger("DockerProvider")
logger.setLevel(logging.DEBUG)


def docker_provider_default_key_name():
    user = os.environ.get('USER') or 'USER'
    return "{0}_molns_docker_sshkey_{1}".format(user, hex(int(time.time())).replace('0x', ''))


class DockerBase(ProviderBase):
    """ Abstract class for Docker. """

    SSH_KEY_EXTENSION = ".pem"
    PROVIDER_TYPE = 'Docker'


class DockerProvider(DockerBase):
    """ Provider handle for local Docker service. """

    OBJ_NAME = 'DockerProvider'

    CONFIG_VARS = OrderedDict([
        ('ubuntu_image_name',
         {'q': 'Base Ubuntu image to use', 'default': Constants.Constants.DOCKER_DEFAULT_IMAGE,
          'ask': True}),
        ('molns_image_name',
         {'q': 'Local MOLNs image name to use', 'default': None, 'ask': True})
    ])

    def check_ssh_key(self):
        """ Returns true, because Docker does not use SSH.
        """
        return True

    def create_ssh_key(self):
        """ Does nothing. """
        return True

    def check_security_group(self):
        """ Does nothing."""
        return True

    def create_seurity_group(self):
        """ Does nothing. """

    def create_molns_image(self):
        """ Create the molns image and save it locally. """
        self._connect()

        # create container
        container = self.docker.create_container()

        # install software
        try:
            logger.debug("Installing software on container ID: {0}".format(container.get('Id')))
            self._run_commands(container, installSoftware.InstallSW.get_command_list())
        except Exception as e:
            logger.exception(e)
            raise ProviderException("Failed to create molns image: {0}".format(e))
        finally:
            logger.debug("Stopping container {0}".format(container))
            self.docker.stop_containers([container])

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
        self.docker = Docker.Docker()
        self.connected = True

    def _run_commands(self, container, commands):
        """Run given commands in the given container. Fails if even a single command returns non-zero error code. """

        # Start container and exec given commands in it.

        self._connect()

        for entry in commands:
            if isinstance(entry, list):
                for sub_entry in entry:
                    ret_val, response = self.docker.execute_command(container, sub_entry)
                    if ret_val is None or ret_val.get('ExitCode') != 0:
                        raise installSoftware.InstallSWException()
            else:
                ret_val, response = self.docker.execute_command(container, entry)
                if ret_val is None or ret_val.get('ExitCode') != 0:
                        raise installSoftware.InstallSWException()


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
