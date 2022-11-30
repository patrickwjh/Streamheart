# -*- coding: utf-8 -*-

import aiohttp
import asyncio


class RequestError(Exception):
    """
    Raised if the request fails
    """
    def __init__(self, error='', message='', status=''):
        super().__init__()
        self.error = error
        self.message = message
        self.status = status


async def get_clips(session, token, client_id, broadcaster_id, first=None, started_at=None, ended_at=None, after=None,
                    before=None):
    headers = {'Authorization': f'Bearer {token}', 'Client-Id': client_id}
    params = {'broadcaster_id': broadcaster_id}

    if first: params['first'] = first
    if started_at: params['started_at'] = started_at
    if ended_at: params['ended_at'] = ended_at
    if after: params['after'] = after
    if before: params['before'] = before

    async with session.get('https://api.twitch.tv/helix/clips', headers=headers, params=params) as response:
        return await _response_return(response)


async def get_users(session, token, client_id, login=None, user_id=None):
    headers = {'Authorization': f'Bearer {token}', 'Client-Id': client_id}

    if not login:
        params = {}
    elif isinstance(login, str):
        params = {'login': login}
    else:
        params = [('login', name) for name in login]

    if not user_id:
        pass
    elif isinstance(user_id, str):
        params = {'id': user_id}
    else:
        params = [('login', user) for user in user_id]

    async with session.get('https://api.twitch.tv/helix/users', headers=headers, params=params) as response:
        return await _response_return(response)


async def _response_return(response):
    if response.status == 200:
        return await response.json()
    else:
        if response.content_type == 'application/json':
            response = await response.json()
            raise RequestError(response.get('error'), response.get('message'), response.get('status'))

        raise RequestError(message="Unknown response error")


async def main():
    async with aiohttp.ClientSession() as session:
        try:
            response = await get_users(session, 'xxx', 'xxx', 'xxx')
            print(response)
            print(type(response))
        except RequestError as error:
            print(error.message)

if __name__ == "__main__":
    asyncio.run(main())
