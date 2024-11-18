import docker


def remove_all_containers(prefix: str):
    try:
        docker_client = docker.from_env()
        containers = docker_client.containers.list(all=True)
        for container in containers:
            try:
                if container.name.startswith(prefix):
                    # container.remove(force=True)
                    pass
            except docker.errors.APIError:
                pass
            except docker.errors.NotFound:
                pass
    except docker.errors.DockerException:
        pass
