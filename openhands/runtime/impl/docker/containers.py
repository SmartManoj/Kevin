import docker


def stop_all_containers(prefix: str) -> None:
    try:
        docker_client = docker.from_env()
        containers = docker_client.containers.list(all=True)
        for container in containers:
            try:
                if container.name.startswith(prefix):
                    # TODO: use config to stop containers
                    # container.stop()
                    pass
            except docker.errors.APIError:
                pass
            except docker.errors.NotFound:
                pass
    except docker.errors.DockerException:
        pass
    finally:
        docker_client.close()
