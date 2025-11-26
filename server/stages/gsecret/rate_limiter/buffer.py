import datetime
import time
from enum import Enum
from threading import Event, Lock, Thread

from pydantic import BaseModel


class IDType(Enum):
    GET_BY_ID = "get_by_id"
    GET_BY_KEY = "get_by_key"


class BufferDelay:
    def __init__(self, timeout: float):
        self.event = Event()
        self.delay_seconds = timeout
        self.creation_time = time.time()

    def wait(self) -> bool:
        return self.event.wait(self.delay_seconds)

    @property
    def expirary_delay(self) -> float:
        return self.delay_seconds - (time.time() - self.creation_time)

    @property
    def expired(self) -> bool:
        return self.expirary_delay <= 0


class BufferRateLimits(BaseModel):
    remaining: int
    resets: datetime.datetime


class BufferedStageClient:
    def __init__(self, controller: "BufferController", default_delay: float = 2.0):
        self.controller = controller
        self.secret_id_api_map: dict[str, str] = {}
        self.secret_key_api_map: dict[str, str] = {}
        self.default_delay = default_delay

    def register_id_api_map(self, secret_id: str, api_id: str):
        self.secret_id_api_map[secret_id] = api_id

    def register_key_api_map(self, secret_key: str, api_id: str):
        self.secret_key_api_map[secret_key] = api_id

    def id_delay(self, secret_id: str, api_delay: BufferDelay):
        if secret_id not in self.secret_id_api_map:
            time.sleep(self.default_delay)
            return
        api_name = self.secret_id_api_map[secret_id]
        if not self.controller.has_rate_limit(api_name):
            time.sleep(self.default_delay)
            return
        self.controller.add_api_delay(api_name, api_delay)
        api_delay.wait()

    def key_delay(self, secret_key: str, api_delay: BufferDelay):
        if secret_key not in self.secret_key_api_map:
            time.sleep(self.default_delay)
            return
        api_name = self.secret_key_api_map[secret_key]
        if not self.controller.has_rate_limit(api_name):
            time.sleep(self.default_delay)
            return
        self.controller.add_api_delay(api_name, api_delay)
        api_delay.wait()

    def log_key_rate_limit(
        self, secret_key: str, api_id: str, rate_limit: BufferRateLimits
    ):
        self.register_key_api_map(secret_key, api_id)
        self.controller.log_rate_limit(api_id, rate_limit)

    def log_id_rate_limit(
        self, secret_id: str, api_id: str, rate_limit: BufferRateLimits
    ):
        self.register_id_api_map(secret_id, api_id)
        self.controller.log_rate_limit(api_id, rate_limit)


class BufferQueue:
    def __init__(self):
        self.queue: dict[str, list[BufferDelay]] = {}
        self.queue_lock = Lock()
        self.queue_has_items = Event()

    def add_delay(self, api_name: str, api_delay: BufferDelay):
        with self.queue_lock:
            if api_name not in self.queue:
                self.queue[api_name] = []
            self.queue[api_name].append(api_delay)
            self.queue_has_items.set()

    def wait_for_items(self):
        self.queue_has_items.wait()

    def get_delays(self, ignore: set[str]) -> dict[str, BufferDelay]:
        delays = {}
        with self.queue_lock:
            for api_name in list(self.queue.keys()):
                if api_name in ignore:
                    continue
                if not self.queue[api_name]:
                    continue
                delay = self.queue[api_name].pop(0)
                delays[api_name] = delay
            if not delays:
                self.queue_has_items.clear()
        return delays


class BufferController:
    def __init__(self):
        self.api_buffers = BufferQueue()
        self.api_rate_limits: dict[str, BufferRateLimits] = {}
        self.controller_thread = Thread(target=self._process_buffers, daemon=True)
        self.controller_thread.start()

    def _delay_from_rate_limit(self, rate_limit: BufferRateLimits) -> float:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        reset_delta = (rate_limit.resets - now).total_seconds()
        if reset_delta < 0:
            return 0.0

        return reset_delta / max(rate_limit.remaining * 0.95, 1)

    def has_rate_limit(self, api_name: str) -> bool:
        return api_name in self.api_rate_limits

    def _process_buffers(self):
        all_delays = {}
        while True:
            self.api_buffers.wait_for_items()
            all_delays = self.api_buffers.get_delays(set(all_delays.keys()))
            min_delay = 0
            min_api: str | None = None
            for api_name, delay in list(all_delays.items()):
                rate_limit = self.api_rate_limits.get(api_name)
                if rate_limit is None:
                    continue
                delay_seconds = self._delay_from_rate_limit(rate_limit)
                if delay_seconds == 0:
                    delay.event.set()
                    all_delays.pop(api_name)
                    continue
                if min_delay == 0 or (delay_seconds < min_delay):
                    min_delay = delay_seconds
                    min_api = api_name
            if min_delay > 0 and min_api is not None:
                print(f"slept for {min_delay} seconds on api {min_api}")
                time.sleep(min_delay)
                delay = all_delays.pop(min_api)
                delay.event.set()

    def add_api_delay(self, api_name: str, api_delay: BufferDelay) -> bool:
        self.api_buffers.add_delay(api_name, api_delay)
        return True

    def log_rate_limit(self, api_name: str, rate_limit: BufferRateLimits):
        self.api_rate_limits[api_name] = rate_limit
