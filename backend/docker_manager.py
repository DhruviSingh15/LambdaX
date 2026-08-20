import docker
from typing import Dict, Any, Optional

class DockerManager:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            print(f"Warning: Could not connect to Docker. Ensure Docker is running. Error: {e}")
            self.client = None

    def create_container(self, image: str, command: Optional[str] = None, name: Optional[str] = None) -> Any:
        if not self.client:
            raise Exception("Docker client not initialized")
        return self.client.containers.create(image, command=command, name=name, detach=True)

    def start_container(self, container_id: str):
        if not self.client:
            raise Exception("Docker client not initialized")
        container = self.client.containers.get(container_id)
        container.start()

    def stop_container(self, container_id: str):
        if not self.client:
            raise Exception("Docker client not initialized")
        container = self.client.containers.get(container_id)
        container.stop()

    def remove_container(self, container_id: str):
        if not self.client:
            raise Exception("Docker client not initialized")
        container = self.client.containers.get(container_id)
        container.remove(force=True)

    def get_container(self, container_id: str) -> Any:
        if not self.client:
            raise Exception("Docker client not initialized")
        return self.client.containers.get(container_id)

    def get_all_containers(self, filters=None):
        if not self.client:
            return []
        return self.client.containers.list(all=True, filters=filters)

    def build_image(self, path: str, tag: str):
        if not self.client:
            raise Exception("Docker client not initialized")
        return self.client.images.build(path=path, tag=tag)

docker_manager = DockerManager()
