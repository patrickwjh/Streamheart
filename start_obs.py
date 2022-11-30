#!/usr/bin/python3
# -*- coding: utf-8 -*-

import asyncio
import argparse
from obs import client
from misc import starter


def start():
    asyncio.run(
        client.start(args.host_middleware, args.port_middleware, args.host_obs, args.port_obs, args.cert),
        debug=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Client to connect Middleware with OBS Studio')
    parser.add_argument('--host_middleware', help='Middleware host address')
    parser.add_argument('--port_middleware', type=int, help='Middleware port')
    parser.add_argument('--host_obs', help='OBS Studio host address')
    parser.add_argument('--port_obs', type=int, help='OBS Studio port')
    parser.add_argument('--cert', help='Path to certificate file')
    parser.add_argument('-s', '--signal', choices=['stop'], help='Shut down gracefully')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()

    starter.run('obs', start, parser)
