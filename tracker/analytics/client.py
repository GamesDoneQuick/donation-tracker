# Adapted from https://github.com/GamesDoneQuick/analytics-packages/blob/0.1.0/analytics.py
# until that package stabilizes
import atexit
from datetime import datetime, date, timedelta
from decimal import Decimal
import json
import logging
from threading import Thread
import time
from typing import Dict, Any
from queue import Queue, Empty

import requests


class AnalyticsClient:
    logger = logging.getLogger('analytics')

    class Config:
        ingest_url: str

        def __init__(
            self,
            *,
            ingest_host: str = 'http://localhost:5000',
            # Maximum number of buffered events before `flush` will be called
            # automatically to avoid an overflow.
            max_buffer_size: int = 100,
            # Maximum amount of time in seconds to wait before automatically
            # flushing the event buffer
            max_wait_time: float = 2.0,
            # Don't emit any events to the ingest host. Tracks will still work
            # and be buffered, but no HTTP calls will be made.
            no_emit: bool = False,
            # Use the `test_path` endpoint instead of actually ingesting events.
            test_mode: bool = False,
            path: str = '/track',
            test_path: str = '/test',
        ):
            self.ingest_host = ingest_host
            self.max_buffer_size = max_buffer_size
            self.max_wait_time = max_wait_time
            self.no_emit = no_emit
            self.path = path
            self.test_path = test_path
            self.test_mode = test_mode

            resolved_path = test_path if test_mode else path
            self.ingest_url = f'{ingest_host}{resolved_path}'

    def __init__(self, config: Config):
        self.config = config
        self.queue = Queue(maxsize=0)
        self.consumer = Consumer(self.config, self.queue)
        atexit.register(self.join)
        # Only start the Consumer if we are going to be emitting events.
        if not self.config.no_emit:
            self.consumer.start()

    def track(self, event_name: str, data: Dict[str, Any]):
        """Track a single analytics event."""
        event_content = {'event_name': str(event_name), 'properties': data}
        self.logger.debug(f'[Analytics Client] Tracked event: {event_content}')
        self.queue.put(event_content)

    def join(self):
        """Allow the consumer thread to gracefully finish before returning."""
        self.consumer.pause()
        try:
            self.consumer.join()
        # This can raise if the consumer thread was never started
        except RuntimeError:
            pass

    def flush(self):
        """
        Force the current queue of events to be uploaded to the ingest host
        immediately. This shouldn't really need to be called most of the time.
        """
        size = self.queue.qsize()
        self.queue.join()
        self.logger.debug(f'[Analytics Client] Forcefully flushed {size} events')


class Consumer(Thread):
    logger = logging.getLogger('analytics')

    def __init__(self, config: AnalyticsClient.Config, queue: Queue):
        Thread.__init__(self)
        self.config = config
        self.queue = queue
        self.daemon = True
        self.running = True

    def pause(self):
        self.running = False

    def run(self):
        while self.running:
            batch = self._get_batch()

            try:
                self.upload(batch)
            except Exception as e:
                self.logger.error('[Analytics Consumer] Failed to process events', e)
            finally:
                for _ in batch:
                    self.queue.task_done()

    def _get_batch(self):
        start = time.monotonic()
        events = []

        while len(events) < self.config.max_buffer_size:
            elapsed = time.monotonic() - start
            if elapsed > self.config.max_wait_time:
                break

            remaining = self.config.max_wait_time - elapsed
            try:
                event = self.queue.get(block=True, timeout=remaining)
                events.append(event)
            except Empty:
                break

        return events

    def upload(self, events):
        if len(events) == 0:
            return

        """Send all buffered events to the ingest server."""
        return requests.post(
            self.config.ingest_url,
            data=json.dumps(events, cls=AnalyticsJSONEncoder),
            headers={'Content-Type': 'application/json'},
        )


class AnalyticsJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # Datetimes are formatted to ISO format
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        # Time deltas are formatted to milliseconds with decimal precision
        if isinstance(obj, timedelta):
            return obj / timedelta(milliseconds=1)
        if isinstance(obj, Decimal):
            return str(obj)

        return json.JSONEncoder.default(self, obj)
