def get_user_id():
    import pwd, os
    return pwd.getpwnam(os.environ['SUDO_USER']).pw_uid


def get_group_id():
    import grp, os
    return grp.getgrnam((os.environ['SUDO_USER'])).gr_gid


class Log:
    verbose = True

    def __init__(self):
        pass

    @staticmethod
    def write_log(message):
        if Log.verbose:
            print message
