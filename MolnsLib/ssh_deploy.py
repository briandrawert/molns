import json
import logging
import os
import paramiko
import string
import sys
import time
import uuid
import webbrowser
import urllib2
import ssl

class SSHDeployException(Exception):
    pass

class SSHDeploy:
    '''
    This class is used for deploy IPython
    '''
    DEFAULT_STOCHSS_PORT = 443
    DEFAULT_INTERNAL_STOCHSS_PORT = 8080
    DEFAULT_GAE_ADMIN_PORT = 8000
    DEFAULT_PRIVATE_NOTEBOOK_PORT = 8090
    DEFAULT_PUBLIC_NOTEBOOK_PORT = 443
    DEFAULT_PRIVATE_WEBSERVER_PORT = 8001
    DEFAULT_PUBLIC_WEBSERVER_PORT = 80
    SSH_CONNECT_WAITTIME = 5
    MAX_NUMBER_SSH_CONNECT_ATTEMPTS = 25
    DEFAULT_SSH_PORT = 22
    DEFAULT_IPCONTROLLER_PORT = 9000
    STOCHSS_SSL_CERT_FILE = 'stochss-ssl_cert.pem'
    STOCHSS_SSL_KEY_FILE = 'stochss-ssl_key.pem'

    DEFAULT_PYURDME_TEMPDIR="/mnt/pyurdme_tmp"


    def __init__(self, config=None, config_dir=None):
        if config is None:
            raise SSHDeployException("No config given")
        self.config = config
        self.config_dir = config_dir
        if config_dir is None:
            self.config_dir = os.path.join(os.path.dirname(__file__), '/../.molns/')
        self.username = config['login_username']
        self.endpoint = self.DEFAULT_PRIVATE_NOTEBOOK_PORT
        self.ssh_endpoint = self.DEFAULT_SSH_PORT
        self.keyfile = config.sshkeyfilename()
        self.provider_name = config.name
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.profile = 'default'
        self.profile_dir = "/home/%s/.ipython/profile_default/" %(self.username)
        self.ipengine_env = 'export INSTANT_OS_CALL_METHOD=SUBPROCESS;export PYURDME_TMPDIR={0};'.format(self.DEFAULT_PYURDME_TEMPDIR)
        self.profile_dir_server = self.profile_dir
        self.profile_dir_client = self.profile_dir
        self.ipython_port = self.DEFAULT_IPCONTROLLER_PORT


    def scp_command(self, hostname):    
        return "scp -o 'StrictHostKeyChecking no' \
                %s@%s:%ssecurity/ipcontroller-engine.json %ssecurity/" \
                %(self.username, hostname, self.profile_dir_server, self.profile_dir_client)

    def prompt_for_password(self):
        import getpass
        while True:
            print "Choose a password to access the IPython interface."
            pw1 = getpass.getpass()
            print "Reenter password."
            pw2 = getpass.getpass()
            if pw1 == pw2:
                print "Success."
                return pw1
            else:
                print "Passwords do not match, try again."

    def create_ssl_cert(self, cert_directory, cert_name_prefix, hostname):
        self.exec_command("mkdir -p '{0}'".format(cert_directory))
        user_cert = cert_directory + '{0}-user_cert.pem'.format(cert_name_prefix)
        ssl_key = cert_directory + '{0}-ssl_key.pem'.format(cert_name_prefix)
        ssl_cert = cert_directory + '{0}-ssl_cert.pem'.format(cert_name_prefix)
        ssl_subj = "/C=CN/ST=SH/L=STAR/O=Dis/CN=%s" % hostname 
        self.exec_command(
            "openssl req -new -newkey rsa:4096 -days 365 "
            '-nodes -x509 -subj %s -keyout %s -out %s' %
            (ssl_subj, ssl_key, ssl_cert))
        return (ssl_key, ssl_cert)

    def create_ipython_config(self, hostname, notebook_password=None):
        (ssl_key, ssl_cert) = self.create_ssl_cert(self.profile_dir_server, self.username, hostname)
        remote_file_name = '%sipython_notebook_config.py' % self.profile_dir_server
        notebook_port = self.endpoint
        sha1py = 'from IPython.lib import passwd; print passwd("%s")'
        sha1cmd = "python -c '%s'" % sha1py
        if notebook_password is None:
            passwd = self.prompt_for_password()
        else:
            passwd = notebook_password
        try:
            sha1pass_out = self.exec_command(sha1cmd % passwd , verbose=False)
            sha1pass = sha1pass_out[0].strip()
        except Exception as e:
            print "Failed: {0}\t{1}:{2}".format(e, hostname, self.ssh_endpoint)
            raise e
        
        sftp = self.ssh.open_sftp()
        notebook_config_file = sftp.file(remote_file_name, 'w+')
        notebook_config_file.write('\n'.join([ 
                "c = get_config()",
                "c.IPKernelApp.pylab = 'inline'",
                "c.NotebookApp.certfile = u'%s'" % ssl_cert,
                "c.NotebookApp.keyfile =  u'%s'" % ssl_key,
                "c.NotebookApp.ip = '*'",
                "c.NotebookApp.open_browser = False",
                "c.NotebookApp.password = u'%s'" % sha1pass,
                "c.NotebookApp.port = %d" % int(notebook_port),
                #"c.Global.exec_lines = ['import dill', 'from IPython.utils import pickleutil', 'pickleutil.use_dill()', 'import logging','logging.getLogger(\'UFL\').setLevel(logging.ERROR)','logging.getLogger(\'FFC\').setLevel(logging.ERROR)']",
                ]))
        notebook_config_file.close()
        
        remote_file_name='%sipcontroller_config.py' % self.profile_dir_server
        notebook_config_file = sftp.file(remote_file_name, 'w+')
        notebook_config_file.write('\n'.join([
                "c = get_config()",
                "c.IPControllerApp.log_level=20",
                "c.HeartMonitor.period=10000",
                "c.HeartMonitor.max_heartmonitor_misses=10",
                "c.HubFactory.db_class = \"SQLiteDB\"",
                ]))
        notebook_config_file.close()

#        # IPython startup code
#        remote_file_name='{0}startup/molns_dill_startup.py'.format(self.profile_dir_server)
#        dill_init_file = sftp.file(remote_file_name, 'w+')
#        dill_init_file.write('\n'.join([
#                'import dill',
#                'from IPython.utils import pickleutil',
#                'pickleutil.use_dill()',
#                'import logging',
#                "logging.getLogger('UFL').setLevel(logging.ERROR)",
#                "logging.getLogger('FFC').setLevel(logging.ERROR)"
#                "import cloud",
#                "logging.getLogger('Cloud').setLevel(logging.ERROR)"
#                ]))
#        dill_init_file.close()
        sftp.close()

    def create_s3_config(self):
        sftp = self.ssh.open_sftp()
        remote_file_name='.molns/s3.json'
        s3_config_file = sftp.file(remote_file_name, 'w')
        config = {}
        config["provider_type"] = self.config.type
        config["bucket_name"] = "molns_storage_{1}_{0}".format(self.get_cluster_id(), self.provider_name)
        config["credentials"] = self.config.get_config_credentials()
        # Only used for OpenStack, Keystone auth API version (2.0 or 3.0)
        config["auth_version"] = self.config["auth_version"]
        s3_config_file.write(json.dumps(config))
        s3_config_file.close()
        sftp.close()

    def get_cluster_id(self):
        """ retreive the cluster id from the config. """
        filename = os.path.join(self.config_dir, 'cluster_id')
        if not os.path.isfile(filename):
            new_id = str(uuid.uuid4())
            logging.debug("get_cluster_id() file {0} not found, creating id = {1}".format(filename, new_id))
            with open(filename, 'w+') as wfd:
                wfd.write(new_id)
        with open(filename) as fd:
            idstr = fd.readline().rstrip()
            logging.debug("get_cluster_id() file {0} found id = {1}".format(filename,idstr))
            if idstr is None or len(idstr) == 0:
                raise SSHDeployException("error getting id for cluster from file, please check your file '{0}'".format(filename))
            return idstr


    def create_engine_config(self):
        sftp = self.ssh.open_sftp()
        remote_file_name='%sipengine_config.py' % self.profile_dir_server
        notebook_config_file = sftp.file(remote_file_name, 'w+')
        notebook_config_file.write('\n'.join([
                "c = get_config()",
                "c.IPEngineApp.log_level=20",
                "c.IPEngineApp.log_to_file = True",
                "c.Global.exec_lines = ['import dill', 'from IPython.utils import pickleutil', 'pickleutil.use_dill()']",
                ]))
        notebook_config_file.close()
        sftp.close()
        self.create_s3_config()

    def _get_ipython_client_file(self):
        sftp = self.ssh.open_sftp()
        engine_file = sftp.file(self.profile_dir_server + 'security/ipcontroller-client.json', 'r')
        engine_file.prefetch(file_size=None)
        file_data = engine_file.read()
        engine_file.close()
        sftp.close()
        return file_data
    
    def _put_ipython_client_file(self, file_data):
        sftp = self.ssh.open_sftp()
        engine_file = sftp.file(self.profile_dir_server + 'security/ipcontroller-client.json', 'w+')
        engine_file.write(file_data)
        engine_file.close()
        sftp.close()

    def _get_ipython_engine_file(self):
        sftp = self.ssh.open_sftp()
        engine_file = sftp.file(self.profile_dir_server + 'security/ipcontroller-engine.json', 'r')
        engine_file.prefetch(file_size=None)
        file_data = engine_file.read()
        engine_file.close()
        sftp.close()
        return file_data
    
    def _put_ipython_engine_file(self, file_data):
        sftp = self.ssh.open_sftp()
        engine_file = sftp.file(self.profile_dir_server + 'security/ipcontroller-engine.json', 'w+')
        engine_file.write(file_data)
        engine_file.close()
        sftp.close()

    def exec_command_list_switch(self, command_list):
        for command in command_list:
            self.exec_command(command)

    def exec_command(self, command, verbose=True):
        try:
            stdout_data = []
            stderr_data = []
            session = self.ssh.get_transport().open_session()
            session.exec_command(command)
            nbytes = 4096
            #TODO add a timeout here, don't wait for commands forever.
            while True:
                if session.recv_ready():
                    msg = session.recv(nbytes)
                    stdout_data.append(msg)
                if session.recv_stderr_ready():
                    msg = session.recv_stderr(nbytes)
                    stderr_data.append(msg)
                if session.exit_status_ready():
                    break
                time.sleep(0.1) # Sleep breifly to prevent over-polling

            status = session.recv_exit_status()
            str_return = ''.join(stdout_data).splitlines()
            stderr_str = ''.join(stderr_data)
            session.close()
            if status != 0:
                raise paramiko.SSHException("Exit Code: {0}\tSTDOUT: {1}\tSTDERR: {2}\n\n".format(status, "\n".join(str_return), stderr_str))
            if verbose:
                print "EXECUTING...\t{0}".format(command)
            return str_return
        except paramiko.SSHException as e:
            if verbose:
                print "FAILED......\t{0}\t{1}".format(command,e)
            raise SSHDeployException("{0}\t{1}".format(command,e))

    def exec_multi_command(self, command, next_command):
        try:
            stdin, stdout, stderr = self.ssh.exec_command(command)
            stdin.write(next_command)
            stdin.flush()
            status = stdout.channel.recv_exit_status()
            if status != 0:
                raise paramiko.SSHException("Exit Code: {0}\tSTDOUT: {1}\tSTDERR: {2}\n\n".format(status, stdout.read(), stderr.read()))
        except paramiko.SSHException as e:
            print "FAILED......\t{0}\t{1}".format(command,e)
            raise e
            
    def connect(self, hostname, port):
        print "Connecting to {0}:{1} keyfile={2}".format(hostname,port,self.keyfile)
        for i in range(self.MAX_NUMBER_SSH_CONNECT_ATTEMPTS):
            try:
                self.ssh.connect(hostname, port, username=self.username,
                    key_filename=self.keyfile)
                print "SSH connection established"
                return
            except Exception as e:
                print "Retry in {0} seconds...\t\t{1}".format(self.SSH_CONNECT_WAITTIME,e)
                time.sleep(self.SSH_CONNECT_WAITTIME)
        raise SSHDeployException("ssh connect Failed!!!\t{0}:{1}".format(hostname,self.ssh_endpoint))

    def deploy_molns_webserver(self, ip_address):
        try:
            self.connect(ip_address, self.ssh_endpoint)
            self.exec_command("sudo rm -rf /usr/local/molns_webroot")
            self.exec_command("sudo mkdir -p /usr/local/molns_webroot")
            self.exec_command("sudo chown ubuntu /usr/local/molns_webroot")
            self.exec_command("git clone https://github.com/Molns/MOLNS_web_landing_page.git /usr/local/molns_webroot")
            self.exec_multi_command("cd /usr/local/molns_webroot; python -m SimpleHTTPServer {0} > ~/.molns_webserver.log 2>&1 &".format(self.DEFAULT_PRIVATE_WEBSERVER_PORT), '\n')
            self.exec_command("sudo iptables -t nat -A PREROUTING -i eth0 -p tcp --dport {0} -j REDIRECT --to-port {1}".format(self.DEFAULT_PUBLIC_WEBSERVER_PORT,self.DEFAULT_PRIVATE_WEBSERVER_PORT))
            self.ssh.close()
            print "Deploying MOLNs webserver"
            url = "http://{0}/".format(ip_address)
            while True:
                try:
                    req = urllib2.urlopen(url)
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    break
                except Exception as e:
                    #sys.stdout.write("{0}".format(e))
                    sys.stdout.write(".")
                    sys.stdout.flush()
                    time.sleep(1)
            webbrowser.open(url)
        except Exception as e:
            print "Failed: {0}\t{1}:{2}".format(e, ip_address, self.ssh_endpoint)
            raise sys.exc_info()[1], None, sys.exc_info()[2]

    def get_number_processors(self):
        cmd = 'python -c "import multiprocessing;print multiprocessing.cpu_count()"'
        try:
            output = self.exec_command(cmd)[0].strip()
            return int(output)
        except Exception as e:
            raise SSHDeployException("Could not determine the number of processors on the remote system: {0}".format(e))

    def deploy_stochss(self, ip_address, port=None):
        if port is None:
            port = self.DEFAULT_STOCHSS_PORT
        try:
            print "{0}:{1}".format(ip_address, self.ssh_endpoint)
            self.connect(ip_address, self.ssh_endpoint)
            sftp = self.ssh.open_sftp()
            print "Checking for local SSL certificate file '{0}' and '{1}'".format(self.STOCHSS_SSL_CERT_FILE, self.STOCHSS_SSL_KEY_FILE)
            if os.path.exists(self.STOCHSS_SSL_CERT_FILE) and os.path.exists(self.STOCHSS_SSL_KEY_FILE):
                print "Copying SSL certificate and key files to server"
                self.exec_command("mkdir -p '{0}'".format("/home/ubuntu/.nginx_cert/"))
                ssl_cert = "/home/ubuntu/.nginx_cert/stochss-ssl_cert.pem"
                with open(self.STOCHSS_SSL_CERT_FILE, 'r') as fd:
                    cert_file = sftp.file(ssl_cert, 'w+')
                    cert_file.write(fd.read())
                    cert_file.close()
                ssl_key = "/home/ubuntu/.nginx_cert/stochss-ssl_key.pem"
                with open(self.STOCHSS_SSL_KEY_FILE, 'r') as fd:
                    cert_file = sftp.file(ssl_key, 'w+')
                    cert_file.write(fd.read())
                    cert_file.close()
            else:
                print "Creating self-signed SSL certificate on server"
                (ssl_key, ssl_cert) = self.create_ssl_cert('/home/ubuntu/.nginx_cert/', 'stochss', ip_address)
            print "Configure Nginx"
            with open(os.path.dirname(os.path.abspath(__file__))+os.sep+'..'+os.sep+'templates'+os.sep+'nginx.conf') as fd:
                web_file = sftp.file("/tmp/nginx.conf", 'w+')
                buff = fd.read()
                buff = string.replace(buff, '###LISTEN_PORT###', str(port))
                buff = string.replace(buff, '###SSL_CERT###', str(ssl_cert))
                buff = string.replace(buff, '###SSL_CERT_KEY###', str(ssl_key))
                web_file.write(buff)
                web_file.close()
            self.exec_command("sudo chown root /tmp/nginx.conf")
            self.exec_command("sudo mv /tmp/nginx.conf /etc/nginx/nginx.conf")
            print "Starting Nginx"
            self.exec_command("sudo nginx")

            #print "Checking out latest development version"
            #self.exec_command("cd /usr/local/stochss && git fetch && git checkout saas && git pull origin saas")

            print "Configuring StochSS"
            admin_token = uuid.uuid4()
            create_and_exchange_admin_token = "python /usr/local/stochss/generate_admin_token.py {0}".format(admin_token)
            self.exec_command(create_and_exchange_admin_token)

            print "Starting StochSS"
            self.exec_command("cd /usr/local/stochss/ && screen -d -m ./run.ubuntu.sh --no_browser -t {0} -a {1}".format(admin_token, ip_address))

            print "Staring redirector from port 80"
            self.exec_command("cd /usr/local/stochss/utils/ && screen -d -m sudo python port80redirect.py")

            stochss_url = "https://{0}:{1}/".format(ip_address,port)
            print "Waiting for StochSS to become available at {0}".format(stochss_url)

            cnt=0;cnt_max=60
            while cnt<cnt_max:
                cnt+=1
                try:
                    try:
                        # works only for Python >= 2.7.9 
                        context = ssl._create_unverified_context()
                        req = urllib2.urlopen(stochss_url, context=context)
                        break
                    except:
                        # in python < 2.7.9 thre is no verification of the certs
                        req = urllib2.urlopen(stochss_url)
                        break
                except Exception as e:
            #        sys.stdout.write("{0}".format(e))
                    sys.stdout.write(".")
                    sys.stdout.flush()
                    time.sleep(1)
            print "Success!"
            time.sleep(1)
            stochss_url = "{0}login?secret_key={1}".format(stochss_url, admin_token)
            print "StochSS available: {0}".format(stochss_url)
            webbrowser.open_new(stochss_url)
        except Exception as e:
            print "StochSS launch failed: {0}\t{1}:{2}".format(e, ip_address, self.ssh_endpoint)
            raise sys.exc_info()[1], None, sys.exc_info()[2]

    def deploy_ipython_controller(self, ip_address, notebook_password=None):
        controller_hostname =  ''
        engine_file_data = ''
        try:
            print "{0}:{1}".format(ip_address, self.ssh_endpoint)
            self.connect(ip_address, self.ssh_endpoint)
            
            # Set up the symlink to local scratch space
            self.exec_command("sudo mkdir -p /mnt/molnsarea")
            self.exec_command("sudo chown ubuntu /mnt/molnsarea")
            self.exec_command("sudo mkdir -p /mnt/molnsarea/cache")
            self.exec_command("sudo chown ubuntu /mnt/molnsarea/cache")

            self.exec_command("test -e {0} && sudo rm {0} ; sudo ln -s /mnt/molnsarea {0}".format('/home/ubuntu/localarea'))
            
            # Setup symlink to the shared scratch space
            self.exec_command("sudo mkdir -p /mnt/molnsshared")
            self.exec_command("sudo chown ubuntu /mnt/molnsshared")
            self.exec_command("test -e {0} && sudo rm {0} ; sudo ln -s /mnt/molnsshared {0}".format('/home/ubuntu/shared'))
            #
            self.exec_command("sudo mkdir -p {0}".format(self.DEFAULT_PYURDME_TEMPDIR))
            self.exec_command("sudo chown ubuntu {0}".format(self.DEFAULT_PYURDME_TEMPDIR))
            #
            #self.exec_command("cd /usr/local/molnsutil && git pull && sudo python setup.py install")
            self.exec_command("mkdir -p .molns")
            self.create_s3_config()

            self.exec_command("ipython profile create {0}".format(self.profile))
            self.create_ipython_config(ip_address, notebook_password)
            self.create_engine_config()
            self.exec_command("source /usr/local/pyurdme/pyurdme_init; screen -d -m ipcontroller --profile={1} --ip='*' --location={0} --port={2} --log-to-file".format(ip_address, self.profile, self.ipython_port), '\n')
            # Start one ipengine per processor
            num_procs = self.get_number_processors()
            num_engines = num_procs - 2
            for _ in range(num_engines):
                self.exec_command("{1}source /usr/local/pyurdme/pyurdme_init; screen -d -m ipengine --profile={0} --debug".format(self.profile, self.ipengine_env))
            self.exec_command("{1}source /usr/local/pyurdme/pyurdme_init; screen -d -m ipython notebook --profile={0}".format(self.profile, self.ipengine_env))
            self.exec_command("sudo iptables -t nat -A PREROUTING -i eth0 -p tcp --dport {0} -j REDIRECT --to-port {1}".format(self.DEFAULT_PUBLIC_NOTEBOOK_PORT,self.DEFAULT_PRIVATE_NOTEBOOK_PORT))
            self.ssh.close()
        except Exception as e:
            print "Failed: {0}\t{1}:{2}".format(e, ip_address, self.ssh_endpoint)
            raise sys.exc_info()[1], None, sys.exc_info()[2]
        url = "http://%s" %(ip_address)
        print "\nThe URL for your MOLNs cluster is: %s." % url

    def get_ipython_engine_file(self, ip_address):
        try:
            print "{0}:{1}".format(ip_address, self.ssh_endpoint)
            self.connect(ip_address, self.ssh_endpoint)
            engine_file_data = self._get_ipython_engine_file()
            self.ssh.close()
            return engine_file_data
        except Exception as e:
            print "Failed: {0}\t{1}:{2}".format(e, ip_address, self.ssh_endpoint)
            raise sys.exc_info()[1], None, sys.exc_info()[2]

    def get_ipython_client_file(self, ip_address):
        try:
            print "{0}:{1}".format(ip_address, self.ssh_endpoint)
            self.connect(ip_address, self.ssh_endpoint)
            engine_file_data = self._get_ipython_engine_file()
            self.ssh.close()
            return engine_file_data
        except Exception as e:
            print "Failed: {0}\t{1}:{2}".format(e, ip_address, self.ssh_endpoint)
            raise sys.exc_info()[1], None, sys.exc_info()[2]


    def deploy_ipython_engine(self, ip_address, controler_ip, engine_file_data, controller_ssh_keyfile):
        try:
            print "{0}:{1}".format(ip_address, self.ssh_endpoint)
            self.connect(ip_address, self.ssh_endpoint)
            
            # Setup the symlink to local scratch space
            self.exec_command("sudo mkdir -p /mnt/molnsarea")
            self.exec_command("sudo chown ubuntu /mnt/molnsarea")
            self.exec_command("sudo mkdir -p /mnt/molnsarea/cache")
            self.exec_command("sudo chown ubuntu /mnt/molnsarea/cache")


            self.exec_command("test -e {0} && sudo rm {0} ; sudo ln -s /mnt/molnsarea {0}".format('/home/ubuntu/localarea'))
            #
            self.exec_command("sudo mkdir -p {0}".format(self.DEFAULT_PYURDME_TEMPDIR))
            self.exec_command("sudo chown ubuntu {0}".format(self.DEFAULT_PYURDME_TEMPDIR))
            # Setup config for object store
            self.exec_command("mkdir -p .molns")
            self.create_s3_config()
            
            
            # SSH mount the controller on each engine
            remote_file_name='.ssh/id_dsa'
            with open(controller_ssh_keyfile) as fd:
                sftp = self.ssh.open_sftp()
                controller_keyfile = sftp.file(remote_file_name, 'w')
                buff = fd.read()
                print "Read {0} bytes from file {1}".format(len(buff), controller_ssh_keyfile)
                controller_keyfile.write(buff)
                controller_keyfile.close()
                print "Remote file {0} has {1} bytes".format(remote_file_name, sftp.stat(remote_file_name).st_size)
                sftp.close()
            self.exec_command("chmod 0600 {0}".format(remote_file_name))
            self.exec_command("mkdir -p /home/ubuntu/shared")
            self.exec_command("sshfs -o Ciphers=arcfour -o Compression=no -o reconnect -o idmap=user -o StrictHostKeyChecking=no ubuntu@{0}:/mnt/molnsshared /home/ubuntu/shared".format(controler_ip))

            # Update the Molnsutil package: TODO remove when molnsutil is stable
            #self.exec_command("cd /usr/local/molnsutil && git pull && sudo python setup.py install")

            self.exec_command("ipython profile create {0}".format(self.profile))
            self.create_engine_config()
            # Just write the engine_file to the engine
            self._put_ipython_engine_file(engine_file_data)
            # Start one ipengine per processor
            for _ in range(self.get_number_processors()):
                self.exec_command("{1}source /usr/local/pyurdme/pyurdme_init; screen -d -m ipengine --profile={0} --debug".format(self.profile,  self.ipengine_env))

            self.ssh.close()

        except Exception as e:
            print "Failed: {0}\t{1}:{2}".format(e, ip_address, self.ssh_endpoint)
            raise sys.exc_info()[1], None, sys.exc_info()[2]


if __name__ == "__main__":
    sshdeploy = SSHDeploy()
    sshdeploy.deploy_ipython_controller()
