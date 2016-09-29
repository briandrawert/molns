import StringIO
import tarfile
import os
import re


class DockerSSH(object):
    def __init__(self, docker):
        self.docker = docker
        self.container_id = None

    def exec_command(self, command, verbose=True):
        cmd = re.sub("\"", "\\\"", command)  # Escape all occurrences of ".
        ret_val, response = self.docker.execute_command(self.container_id, cmd)
        # print "RESPONSE: " + response
        return response

    def exec_multi_command(self, command, for_compatibility):
        return self.exec_command(command)

    def open_sftp(self):
        return MockSFTP(self.docker, self.container_id)

    def connect(self, instance, port=None, username=None, key_filename=None):
        self.container_id = instance.provider_instance_identifier

    def close(self):
        self.container_id = None


class MockSFTPFileException(Exception):
    pass


class MockSFTP:
    def __init__(self, docker, container_id):
        self.docker = docker
        self.container_id = container_id

    def file(self, filename, flag):
        return MockSFTPFile(filename, flag, self.docker, self.container_id)

    def close(self):
        pass


class MockSFTPFile:
    def __init__(self, filename, flag, docker, container_id):
        self.filename = filename  # Absolute path of file.
        self.file_contents = ""
        self.docker = docker
        self.container_id = container_id
        if flag is 'w':
            self.flag = flag
        else:
            print("WARNING Unrecognized file mode. Filename: {0}, Flag: {1}".format(filename, flag))

    def write(self, write_this):
        self.file_contents += write_this

    def close(self):
        # Make tarfile.
        temp_tar = "transport.tar"
        tar = tarfile.TarFile(temp_tar, "w")
        string = StringIO.StringIO()
        string.write(self.file_contents)
        string.seek(0)
        tar_file_info = tarfile.TarInfo(name=os.path.basename(self.filename))
        tar_file_info.size = len(string.buf)
        tar.addfile(tarinfo=tar_file_info, fileobj=string)
        tar.close()  # Create temporary tar file to be copied into container.

        path_to_file = os.path.dirname(self.filename)
        # create_path_to_file_command = "sudo mkdir -p {0}".format(path_to_file)
        # self.docker.execute_command(self.container_id, create_path_to_file_command)
        # print "PATH TO FILE: " + path_to_file
        with open(temp_tar, mode='rb') as f:
            tar_file_bytes = f.read()
        self.docker.put_archive(self.container_id, tar_file_bytes, path_to_file)
        os.remove(temp_tar)  # Remove temporary tar file.
