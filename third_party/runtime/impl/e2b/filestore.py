from typing import Protocol

from openhands.events.observation.error import ErrorObservation
from openhands.storage.files import FileStore


class SupportsFilesystemOperations(Protocol):
    def write(self, path: str, contents: str | bytes) -> None: ...
    def read(self, path: str) -> str: ...
    def list(self, path: str) -> list[str]: ...
    def delete(self, path: str) -> None: ...


class E2BFileStore(FileStore):
    def __init__(self, filesystem: SupportsFilesystemOperations) -> None:
        self.filesystem = filesystem

    def write(self, path: str, contents: str | bytes) -> None:
        self.filesystem.write(path, contents)

    def read(self, path: str) -> str:
        try:
            return self.filesystem.read(path)
        except Exception as e:
            raise FileNotFoundError(f"File not found: {path}") from e

    def list(self, path: str) -> list[str]:
        try:
            return self.filesystem.list(path)
        except Exception as e:
            return []

    def delete(self, path: str) -> None:
        self.filesystem.delete(path)
