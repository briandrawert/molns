import logging

from Constants import Constants
from docker import Client
from docker.errors import NotFound, NullResource, APIError


class Docker:

    """ A wrapper over docker-py."""

    LOG_TAG = "Docker"

    shell_commands = ["source"]

    def __init__(self):
        self.client = Client(base_url=Constants.DOCKER_BASE_URL)
        self.build_count = 0
        logging.basicConfig(level=logging.DEBUG)

    def create_container(self, image_id=Constants.DOCKER_DEFAULT_IMAGE):
        """Create a new container."""
        logging.debug(Docker.LOG_TAG + " Using image {0}".format(image_id))
        container = self.client.create_container(image=image_id, command="/bin/bash", tty=True, detach=True)
        # TODO self.execute_command(container, "su - ubuntu")
        return container

    def stop_containers(self, containers):
        """Stop given containers."""
        for container in containers:
            self.stop_container(container)

    def stop_container(self, container):
        self.client.stop(container)

    def is_container_running(self, container):
        """Check if container of given name is running or not."""
        return self.client.inspect_container(container.get('Id')).get('State').get('Status')

    def start_containers(self, containers):
        """Start each container object in given list."""
        for container in containers:
            self.start_container(container)

    def start_container(self, container):
        logging.debug(Docker.LOG_TAG + " Starting container " + container.get('Id'))
        try:
            self.client.start(container.get('Id'))
        except (NotFound, NullResource) as e:
            logging.error(Docker.LOG_TAG + " Something went wrong while starting container.", e)
            return False
        return True

    def execute_command(self, container, command):
        logging.debug(Docker.LOG_TAG + " Container ID: {0}         Command: {1}".format(container.get('Id'), command))

        if self.start_container(container) is False:
            logging.error("Docker", " Could not start container.")
            return None

        try:
            exec_instance = self.client.exec_create(container.get('Id'), "/bin/bash -c \"" + command + "\"")
            response = self.client.exec_start(exec_instance)
            return [self.client.exec_inspect(exec_instance), response]
        except (NotFound, APIError) as e:
            logging.error(Docker.LOG_TAG + " Could not execute command.", e)
            return None

    def build_image(self, Dockerfile):
        """ Build image from given Dockerfile object and return build output. """
        self.build_count += 1
        logging.debug("Dockerfile name: " + Dockerfile.name)
        image_tag = "aviralcse/docker-provider-{0}".format(self.build_count)
        for line in self.client.build(fileobj=Dockerfile, rm=True, tag=image_tag):
            print(line)
        return image_tag
