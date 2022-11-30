# -*- coding: utf-8 -*-

import json
import asyncio
import logging
import concurrent.futures
import concurrent.futures.thread
from enum import Enum
from heart_rate import stream_health
from configparser import ConfigParser


class Unit(Enum):
    BPS = 1
    KBPS = 1000
    MBPS = 1000000
    GBPS = 1000000000


STREAMFILE_PATH = "/usr/local/nginx/rtmp/stream"

logger = logging.getLogger(__name__)


class StreamBitrate:
    def __init__(self, config_path):
        self.critical_bitrate = 400000
        self.low_bitrate = 800000
        self.health = stream_health.StreamHealth()
        self.streamfile = None
        self.stream = {}
        self.active = asyncio.Event()
        self.active.set()
        self.pool = concurrent.futures.ThreadPoolExecutor()
        self._load_config(config_path)

    def _load_config(self, path):
        config = ConfigParser()
        config.read(path)

        try:
            heartrate_section = config['HEARTRATE']
            self.critical_bitrate = int(heartrate_section['BRB_BITRATE']) * 1000
            self.low_bitrate = int(heartrate_section['LOW_BITRATE']) * 1000
        except KeyError as error:
            logger.error(f"Load config: Can't find {error}")
            raise

    def _open_file(self):
        file = open(STREAMFILE_PATH, 'r')
        return file

    async def create_file_reader(self):
        rx = asyncio.StreamReader()

        try:
            fd = await asyncio.get_running_loop().run_in_executor(self.pool, self._open_file)
            transport, _ = await asyncio.get_running_loop().connect_read_pipe(
                lambda: asyncio.StreamReaderProtocol(rx), fd)

            return rx, fd, transport
        except OSError as error:
            logger.error(f"Can't open {STREAMFILE_PATH}. {error.strerror}")
            raise

    async def read_file(self):
        fd, transport = None, None

        try:
            self.streamfile, fd, transport = await self.create_file_reader()
            line = await self.streamfile.read()
            logger.debug(line.decode('utf-8'))
            stream = json.loads(line)

            return stream
        except json.JSONDecodeError:
            logger.debug("Stream can't be be parsed to JSON")
            raise
        except OSError:
            raise
        finally:
            if fd and transport:
                transport.close()
                fd.close()

    async def check_health(self):
        await self.active.wait()

        try:
            self.stream = await asyncio.wait_for(self.read_file(), timeout=3.0)
        except asyncio.TimeoutError:
            logger.debug("Read stream timeout. No new data. Stream OFFLINE")
            self.stream["bitrate"] = 0
            self.health.status.update(stream_health.State.OFFLINE)

            return self.health.status.state
        except (json.JSONDecodeError, OSError):
            return stream_health.State.ERROR

        try:
            bitrate = self.stream['bitrate']
        except KeyError:
            logger.error("Can't find bitrate field in stream")
            return stream_health.State.ERROR

        if 0 < bitrate < self.critical_bitrate:
            self.health.status.update(stream_health.State.CRITICAL)
        elif self.critical_bitrate <= bitrate < self.low_bitrate:
            self.health.status.update(stream_health.State.LOW)
        elif self.low_bitrate <= bitrate:
            self.health.status.update(stream_health.State.STABLE)

        return self.health.status.state

    def get_health_state(self):
        return self.health.status.state

    def stop(self):
        self.pool.shutdown(False)
        self.pool._threads.clear()
        concurrent.futures.thread._threads_queues.clear()

    def __repr__(self):
        return f"StreamBitrate(stream: {self.stream}, stream_health: {self.health.status.state.name}," \
               f" active: {self.active}, critical_bitrate: {self.critical_bitrate}, low_bitrate: {self.low_bitrate})"
