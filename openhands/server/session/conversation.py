import asyncio

from openhands.core.config import AppConfig
from openhands.events.stream import EventStream
from openhands.runtime import get_runtime_cls
from openhands.runtime.base import Runtime
from openhands.runtime.impl.docker.docker_runtime import DockerRuntime
from openhands.runtime.impl.remote.remote_runtime import RemoteRuntime
from openhands.security import SecurityAnalyzer, options
from openhands.storage.files import FileStore
from openhands.utils.async_utils import call_sync_from_async


class Conversation:
    sid: str
    file_store: FileStore
    event_stream: EventStream
    runtime: Runtime
    user_id: str | None

    def __init__(
        self, sid: str, file_store: FileStore, config: AppConfig, user_id: str | None
    ):
        self.sid = sid
        self.config = config
        self.file_store = file_store
        self.user_id = user_id
        self.event_stream = EventStream(sid, file_store, user_id)
        if config.security.security_analyzer:
            self.security_analyzer = options.SecurityAnalyzers.get(
                config.security.security_analyzer, SecurityAnalyzer
            )(self.event_stream)

        runtime_cls = get_runtime_cls(self.config.runtime)
        
        kwargs = {}
        if runtime_cls in [RemoteRuntime, DockerRuntime]:
            kwargs['user_id'] = self.user_id

        self.runtime = runtime_cls(
            config=config,
            event_stream=self.event_stream,
            sid=self.sid,
            attach_to_existing=True,
            headless_mode=False,
            **kwargs
        )

    async def connect(self) -> None:
        await self.runtime.connect()

    async def disconnect(self) -> None:
        if self.event_stream:
            self.event_stream.close()
        asyncio.create_task(call_sync_from_async(self.runtime.close))
