class DockerSSH(object):

    def __init__(self, docker):
        self.docker = docker
        self.container_id = None

    def exec_command(self, command, verbose=True):
        self.docker.execute_command(self.container_id, command)

    def open_sftp(self):
        # TODO
        print("DockerSSH open_sftp not yet implemented.")

    def connect(self, instance, port=None, username=None, key_filename=None):
        self.container_id = instance.provider_instance_identifier

    def close(self):
        # TODO
        print("DockerSSH close not yet implemented.")
