class Constants:
    LOGGING_DIRECTORY = "~/MOLNS_LOG"
    DOCKER_BASE_URL = "unix://var/run/docker.sock"
    DOCKER_DEFAULT_IMAGE = "ubuntu:latest"
    DOCKER_DEFAULT_PORT = '9000'
    DOCKER_CONTAINER_RUNNING = "running"
    DOCKER_CONTAINER_EXITED = "exited"
    DOCKERFILE_NAME = "dockerfile_"
    DOKCER_IMAGE_ID_LENGTH = 12
    DOCKER_IMAGE_PREFIX = "aviralcse/docker-provider-"
    DOCKER_PY_IMAGE_ID_PREFIX_LENGTH = 7
    DockerProvider = "Docker"
    DockerNonExistentTag = "**NA**"
    DockerImageDelimiter = "|||"
