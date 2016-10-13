class Log:
    verbose = True

    def __init__(self):
        pass

    @staticmethod
    def write_log(message):
        if Log.verbose:
            print message
