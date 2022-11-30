#!/usr/bin/python3
# -*- coding: utf-8 -*-

import asyncio
import argparse
from misc import starter
from twitch_bot import bot


def start():
    asyncio.run(bot.start(args.config, args.bot_config, args.host, args.port, args.cert), debug=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Twitch bot to control Streamheart')
    parser.add_argument('--host', help='Middleware host address')
    parser.add_argument('--port', type=int, help='Middleware port')
    parser.add_argument('--config', help='Streamheart config path')
    parser.add_argument('--bot_config', help='Bot config path')
    parser.add_argument('--cert', help='Path to certificate file')
    parser.add_argument('-s', '--signal', choices=['stop'], help='Shut down gracefully')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()

    starter.run('twitch_bot', start, parser)
