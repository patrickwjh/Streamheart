#!/usr/bin/python3
# -*- coding: utf-8 -*-

import asyncio
import argparse
from misc import starter
from heart_rate import heart_rate


def start():
    asyncio.run(heart_rate.start(args.config, args.host, args.port, args.cert), debug=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Check stream bitrate and change scenes between BRB and Live if necessary')
    parser.add_argument('--host', help='Middleware host address')
    parser.add_argument('--port', type=int, help='Middleware port')
    parser.add_argument('--config', help='Streamheart config path')
    parser.add_argument('--cert', help='Path to certificate file')
    parser.add_argument('-s', '--signal', choices=['stop'], help='Shut down gracefully')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()

    starter.run('heart_rate', start, parser)
