# -*- coding: utf-8 -*-

import json
import shutil
import aiohttp
import asyncio
import logging
import datetime
from enum import Enum
from twitch import api
from pathlib import Path
from twitch_clips import exceptions

logger = logging.getLogger(__name__)
RFC3339_FORMAT = '%Y-%m-%dT%XZ'
LOOKUP_TABLE_NAME = 'clips.txt'
BACKUP_DIR_NAME = 'Backup'


class TimePeriod(Enum):
    DAY = 1
    WEEK = 7
    MONTH = 31
    TOP = 0


class ClipLoader:
    def __init__(self, directory, session, token, client_id, broadcaster_id, with_lookup_table=True,
                 lookup_table_dir=None, backup_dir=None):
        self.directory = directory
        self._check_directory(self.directory)
        self.session = session
        self.token = token
        self.client_id = client_id
        self.broadcaster_id = broadcaster_id
        self._with_lookup_table = with_lookup_table
        self.clips_lookup_table = {'clips': []}

        if lookup_table_dir:
            self._check_directory(lookup_table_dir)
            self.lookup_table_path = Path(lookup_table_dir).joinpath(LOOKUP_TABLE_NAME)
        else:
            self.lookup_table_path = Path(self.directory).joinpath(LOOKUP_TABLE_NAME)
        if with_lookup_table:
            self._load_lookup_table()
        if backup_dir:
            self.backup_dir = backup_dir
        else:
            self.backup_dir = Path(self.directory).joinpath(BACKUP_DIR_NAME)
        self._check_directory(self.backup_dir)

    async def clips_from_time_period(self, period: TimePeriod, max_number=10):
        if not 1 <= max_number <= 100:
            raise ValueError("max_number must be between 1 and 100")
        date_now = datetime.datetime.now()
        started_date = datetime.date.fromordinal(date_now.toordinal() - period.value)
        started = datetime.datetime.combine(started_date, date_now.time()).strftime(RFC3339_FORMAT)
        ended = date_now.strftime(RFC3339_FORMAT)

        try:
            if period is TimePeriod.TOP:
                clips_data = await api.get_clips(self.session, self.token, self.client_id, self.broadcaster_id,
                                                 max_number)
            else:
                clips_data = await api.get_clips(self.session, self.token, self.client_id, self.broadcaster_id,
                                                 max_number, started, ended)
            return clips_data['data'], clips_data['pagination']['cursor']
        except api.RequestError:
            raise

    async def download_clips(self, data, max_downloads=5):
        chunks = [data[idx:idx+max_downloads] for idx in range(0, len(data), max_downloads)]

        for chunk in chunks:
            coros_download = [self.download_clip(clip_data) for clip_data in chunk]
            await asyncio.gather(*coros_download)

    async def download_clip(self, clip_data):
        if self._with_lookup_table and self._check_if_in_directory(clip_data['clip_id']):
            return

        try:
            url = self.clip_url(clip_data)

            async with self.session.get(url) as response:
                if response.status == 200:
                    path = Path(self.directory).joinpath(f'{clip_data["clip_id"]}.mp4')

                    with open(path, 'wb') as clip_file:
                        clip_file.write(await response.read())

                    if self._with_lookup_table:
                        self.clips_lookup_table['clips'].append(
                            {'id': clip_data["id"], 'title': clip_data["title"], 'url': clip_data['url'],
                             'creator_name': clip_data['creator_name'], 'created_at': clip_data['created_at']})
        except exceptions.ClipUrlError as error:
            logger.error(f"Thumbnail URL syntax changed: {error.url}. Can't load clip")

    def clip_url(self, clip_data):
        thumbnail_url = clip_data['thumbnail_url']
        slice_point = thumbnail_url.find('-preview-')

        if slice_point == -1:
            raise exceptions.ClipUrlError(
                f"Can't find '-preview-' in thumbnail url to create clip url: {thumbnail_url}", thumbnail_url)

        return f'{thumbnail_url[:slice_point]}.mp4'

    def replace_clips(self, data, backup=False):
        if len(data) > 0 and data[0].get('id'):
            new = {clip['id'] for clip in data}
        else:
            new = {clip_id for clip_id in data}

        old = {clip['id'] for clip in self.clips_lookup_table['clips']}
        to_remove = old - new

        for clip_id in to_remove:
            src = Path(self.directory).joinpath(clip_id)
            # TODO remove from lookup_table

            if backup:
                shutil.move(str(src), str(self.backup_dir))

    def _load_lookup_table(self):
        if self.lookup_table_path.exists():
            with open(self.lookup_table_path, 'r') as file:
                self.clips_lookup_table = json.load(file)
        else:
            with open(self.lookup_table_path, 'x') as file:
                json.dump(self.clips_lookup_table, file)

    def _save_lookup_table(self):
        if self.lookup_table_path.exists():
            with open(self.lookup_table_path, 'w') as file:
                json.dump(self.clips_lookup_table, file)
        else:
            with open(self.lookup_table_path, 'x') as file:
                json.dump(self.clips_lookup_table, file)

    def _check_directory(self, path):
        if not Path(path).exists():
            Path(path).mkdir(parents=True)

    def _check_if_in_directory(self, clip_id):
        for clip in self.clips_lookup_table['clips']:
            if clip['clip_id'] == clip_id:
                return True

        return False

    @staticmethod
    async def broadcaster_id(session, token, client_id, username):
        try:
            user_data = await api.get_users(session, token, client_id, username)

            if user_data['data']:
                return user_data['data'][0]['id']
            else:
                return
        except api.RequestError:
            raise


async def start():
    async with aiohttp.ClientSession() as session:
        loader = ClipLoader("/home/patrick/Videos/Clips", session, 'xxx',
                            'xxx', 'xxx')
        try:
            clips = await loader.clips_from_time_period(TimePeriod.TOP)
            print(json.dumps(clips, indent=4))
        except api.RequestError as error:
            print(f"{error.error}, {error.message}, {error.status}")
        await loader.download_clips(await loader.clips_from_time_period(TimePeriod.TOP, 3))

asyncio.run(start())
