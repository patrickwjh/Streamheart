#!/usr/bin/python3
# -*- coding: utf-8 -*-

import asyncio
import argparse
from misc import starter
from heart.server import Server


def start():
    if args.host:
        server = Server(args.host, ssl_cert=(args.cert, args.key))
    elif args.port:
        server = Server(port=args.port, ssl_cert=(args.cert, args.key))
    elif args.host and args.port:
        server = Server(args.host, args.port, (args.cert, args.key))
    else:
        server = Server(ssl_cert=(args.cert, args.key))

    asyncio.run(server.start(), debug=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Middleware websocket for message exchange between applications')
    parser.add_argument('--host', help='Host address')
    parser.add_argument('--port', type=int, help='Port')
    parser.add_argument('--cert', help='Path to certificate file')
    parser.add_argument('--key', help='Path to key file for corresponding certificate')
    parser.add_argument('-s', '--signal', choices=['stop'], help='Shut down gracefully')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()

    starter.run('heart', start, parser)
