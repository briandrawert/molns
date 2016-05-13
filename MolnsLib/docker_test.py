from Docker import Docker

command_list = [

    # Basic contextualization
    "sudo apt-get update",
    "sudo apt-get -y install git",
    "sudo apt-get -y install build-essential python-dev",
    "sudo apt-get -y install python-setuptools",
    "sudo apt-get -y install python-matplotlib python-numpy python-scipy",
    "sudo apt-get -y install make",
    "sudo apt-get -y install python-software-properties",
    "sudo apt-get -y install cython python-h5py",
    "sudo apt-get -y install python-pip python-dev build-essential",
    "sudo pip install pyzmq --upgrade",
    "sudo pip install dill cloud pygments",
    "sudo pip install tornado Jinja2",

    # Molnsutil
    [
        "sudo pip install jsonschema jsonpointer",
        # EC2/S3 and OpenStack APIs
        "sudo pip install boto",
        "sudo apt-get -y install pandoc",
        # This set of packages is needed for OpenStack, as molnsutil uses them for hybrid cloud deployment
        "sudo apt-get -y install libxml2-dev libxslt1-dev python-dev",
        "sudo pip install python-novaclient",
        "sudo easy_install -U pip",
        "sudo pip install python-keystoneclient",
        "sudo pip install python-swiftclient",
    ],

    [
        "sudo rm -rf /usr/local/molnsutil;sudo mkdir -p /usr/local/molnsutil;sudo chown ubuntu /usr/local/molnsutil",
        "cd /usr/local/ && git clone https://github.com/Molns/molnsutil.git",
        "cd /usr/local/molnsutil && sudo python setup.py install"
    ],

    # So the workers can mount the controller via SSHfs
    ["sudo apt-get -y install sshfs",
     "sudo gpasswd -a ubuntu fuse",
     "echo \'ServerAliveInterval 60\' >> /home/ubuntu/.ssh/config",
     ],

    # IPython
    ["sudo rm -rf ipython;git clone --recursive https://github.com/Molns/ipython.git",
     "cd ipython && git checkout 3.0.0-molns_fixes && python setup.py submodule && sudo python setup.py install",
     "sudo rm -rf ipython",
     "ipython profile create default",
     "sudo pip install terminado",  # Jupyter terminals
     "python -c 'from IPython.external import mathjax; mathjax.install_mathjax(tag=\\\"2.2.0\\\")'"
     ],

    ### Simulation software related to pyurdme and StochSS

    # Gillespy
    ["sudo rm -rf /usr/local/StochKit;sudo mkdir -p /usr/local/StochKit;sudo chown ubuntu /usr/local/StochKit",
     "cd /usr/local/ && git clone https://github.com/StochSS/stochkit.git StochKit",
     "cd /usr/local/StochKit && ./install.sh",

     "sudo rm -rf /usr/local/ode-1.0.3;sudo mkdir -p /usr/local/ode-1.0.3/;sudo chown ubuntu /usr/local/ode-1.0.3",
     "wget https://github.com/StochSS/stochss/blob/master/ode-1.0.3.tgz?raw=true -q -O /tmp/ode.tgz",
     "cd /usr/local/ && tar -xzf /tmp/ode.tgz",
     "rm /tmp/ode.tgz",
     "cd /usr/local/ode-1.0.3/cvodes/ && tar -xzf 'cvodes-2.7.0.tar.gz'",
     "cd /usr/local/ode-1.0.3/cvodes/cvodes-2.7.0/ && ./configure --prefix='/usr/local/ode-1.0.3/cvodes/cvodes-2.7.0/cvodes' 1>stdout.log 2>stderr.log",
     "cd /usr/local/ode-1.0.3/cvodes/cvodes-2.7.0/ && make 1>stdout.log 2>stderr.log",
     "cd /usr/local/ode-1.0.3/cvodes/cvodes-2.7.0/ && make install 1>stdout.log 2>stderr.log",
     "cd /usr/local/ode-1.0.3/ && STOCHKIT_HOME=/usr/local/StochKit/ STOCHKIT_ODE=/usr/local/ode-1.0.3/ make 1>stdout.log 2>stderr.log",

     "sudo rm -rf /usr/local/gillespy;sudo mkdir -p /usr/local/gillespy;sudo chown ubuntu /usr/local/gillespy",
     "cd /usr/local/ && git clone https://github.com/MOLNs/gillespy.git",
     "cd /usr/local/gillespy && sudo STOCHKIT_HOME=/usr/local/StochKit/ STOCHKIT_ODE_HOME=/usr/local/ode-1.0.3/ python setup.py install"

     ],

    # FeniCS/Dolfin/pyurdme
    ["sudo add-apt-repository -y ppa:fenics-packages/fenics",
     "sudo apt-get update",
     "sudo apt-get -y install fenics",
     # Gmsh for Finite Element meshes
     "sudo apt-get install -y gmsh",
     ],

    # pyurdme
    ["sudo rm -rf /usr/local/pyurdme;sudo mkdir -p /usr/local/pyurdme;sudo chown ubuntu /usr/local/pyurdme",
     "cd /usr/local/ && git clone https://github.com/MOLNs/pyurdme.git",
     # "cd /usr/local/pyurdme && git checkout develop",  # for development only
     "cp /usr/local/pyurdme/pyurdme/data/three.js_templates/js/* .ipython/profile_default/static/custom/",
     "source /usr/local/pyurdme/pyurdme_init && python -c 'import pyurdme'",
     ],

    # example notebooks
    ["rm -rf MOLNS_notebooks;git clone https://github.com/Molns/MOLNS_notebooks.git",
     "cp MOLNS_notebooks/*.ipynb .;rm -rf MOLNS_notebooks;",
     "ls *.ipynb"
     ],

    # Upgrade scipy from pip to get rid of super-annoying six.py bug on Trusty
    "sudo apt-get -y remove python-scipy",
    "sudo pip install scipy",

    "sudo pip install jsonschema jsonpointer",  # redo this install to be sure it has not been removed.


    "sync",  # This is critical for some infrastructures.
]

docker = Docker()

container = docker.create_container()

docker.start_container(container)

print "is container running: {0}".format(docker.is_container_running(container))


for entry in command_list:
        if isinstance(entry, list):
            for sub_entry in entry:
                ret_val, response = docker.execute_command(container, sub_entry)
                print "RETURN VALUE: {0}".format(ret_val)
                if ret_val is None or ret_val.get('ExitCode') != 0:
                    print "ERROR"
                    print "RESPONSE: {0}".format(response)
                print "__"
                print "__"

        else:
            ret_val, response = docker.execute_command(container, entry)
            print "RETURN VALUE: {0}".format(ret_val)
            if ret_val is None or ret_val.get('ExitCode') != 0:
                print "ERROR"
                print "RESPONSE: {0}".format(response)
            print "__"
            print "__"
