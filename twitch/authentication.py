# -*- coding: utf-8 -*-

import aiohttp
import asyncio


VALIDATION_ENDPOINT = 'https://id.twitch.tv/oauth2/validate'
TOKEN_ENDPOINT = 'https://id.twitch.tv/oauth2/token'
REVOKE_ENDPOINT = 'https://id.twitch.tv/oauth2/revoke'


async def validate(session, access_token):
    header = {'Authorization': f'OAuth {access_token}'}

    async with session.get(VALIDATION_ENDPOINT, headers=header) as response:
        return await response.json()


async def client_credentials_flow(session, client_id, client_secret, scopes=None):
    if scopes is None:
        scope = {}
    else:
        scope = {'scope': " ".join(scopes)}

    params = {**{'client_id': client_id, 'client_secret': client_secret, 'grant_type': 'client_credentials'}, **scope}

    async with session.post(TOKEN_ENDPOINT, params=params) as response:
        return await response.json()


async def revoke(session, client_id, access_token):
    params = {'client_id': client_id, 'token': access_token}

    async with session.post(REVOKE_ENDPOINT, params=params) as response:
        return response.status


async def main():
    async with aiohttp.ClientSession() as session:
        response = await validate(session, "xxx")
        print(response)
        response = await client_credentials_flow(session, 'xxx', 'xxx', ['channel:read:subscriptions', 'channel:manage:broadcast'])
        print(response)

        response = await validate(session, "xxx")
        print(response)

if __name__ == "__main__":
    asyncio.run(main())
