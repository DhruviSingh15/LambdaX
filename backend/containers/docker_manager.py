import docker
from typing import Optional, Any

class DockerManager:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            print(f"Warning: Could not connect to Docker. Ensure Docker is running. Error: {e}")
            self.client = None

    def create_and_start(self, image: str, name: str, memory_mb: int) -> str:
        """Creates and starts a container, keeping it alive. Returns container.id"""
        if not self.client:
            raise Exception("Docker client not initialized")
        
        container = self.client.containers.run(
            image,
            command="sleep infinity", 
            detach=True,
            labels={"lambdax_function": name},
            mem_limit=f"{memory_mb}m"
        )
        return container.id

    def execute_function(self, container_id: str) -> bool:
        """Executes the function inside the warm container."""
        if not self.client:
            raise Exception("Docker client not initialized")
        
        container = self.client.containers.get(container_id)
        # Assuming app.py is the standard entrypoint for now
        exec_result = container.exec_run("python app.py")
        if exec_result.exit_code != 0:
            print(f"Error executing function in {container_id}: {exec_result.output}")
            return False
        return True

    def remove_container(self, container_id: str):
        if not self.client:
            return
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=True)
        except Exception as e:
            print(f"Could not remove container {container_id}: {e}")

    def inspect_container(self, container_id: str) -> str:
        """Returns status of container (e.g. running, exited)"""
        if not self.client:
            return "unknown"
        try:
            container = self.client.containers.get(container_id)
            return container.status
        except docker.errors.NotFound:
            return "removed"

docker_manager = DockerManager()
