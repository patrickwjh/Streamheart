# -*- coding: utf-8 -*-

import sys
import json
import asyncio
import logging
import irc.bot
import irc.client
import irc.client_aio
from irc.dict import IRCDict

logger = logging.getLogger(__name__)
IRC_SERVER = 'irc.chat.twitch.tv'
IRC_SERVER_PORT = 6667


class User:
    def __init__(self, name=None, user_id=None, broadcaster=False, mod=False, sub=False):
        self.name = name
        self.id = user_id
        self.broadcaster = broadcaster
        self.mod = mod
        self.sub = sub

    def __repr__(self):
        return f"User(name={self.name}, id={self.id}, broadcaster={self.broadcaster}, mod={self.mod}, sub={self.sub})"


class Bot(irc.bot.SingleServerIRCBot):
    def __init__(self, config_path, loop):
        self.loop = loop
        self.client_id = None
        self.token = None
        self.channel = None
        self.nick = None
        self.prefix = None
        self.authorize_mods = None
        self.authorize_user = None
        self.command_everyone = None
        self.bot_config(config_path)
        self.ready = asyncio.Event()
        self.commands = {}

        # Create IRC bot connection
        logger.debug(f"Connecting to {IRC_SERVER} on port {IRC_SERVER_PORT}...")
        irc.bot.SingleServerIRCBot.__init__(self, [(IRC_SERVER, IRC_SERVER_PORT, f"oauth:{self.token}")], self.nick,
                                            self.nick)

    def bot_config(self, path):
        with open(path, 'r') as config_file:
            config = json.loads(config_file.read())
            try:
                credentials = config['credentials']
                self.token = credentials['tmiToken']
                self.client_id = credentials['clientID']
                self.nick = credentials['botNick']
                self.prefix = credentials['bot_Prefix']
                self.channel = f'#{credentials["channel"]}'.lower()

                settings = config['settings']
                self.authorize_mods = settings['authorize_mods']
                self.authorize_user = settings['authorize_user']
                self.command_everyone = settings['command_for_everyone']

                return config
            except KeyError as error:
                logger.error(f"Corrupt Twitch bot config file. Can't find {error}. ")

    def _on_disconnect(self, connection, event):
        self.ready.clear()
        self.channels = IRCDict()

        if event.arguments[0] == "Connection reset by peer":
            sys.exit(0)

        self.recon.run(self)
        self.ready.set()

    def die(self, msg="Bye, cruel world!"):
        """Let the bot die.
        Arguments:
            msg -- Quit message.
        """
        self.ready.clear()

        if self.connection.is_connected():
            self.connection.part(self.channel)
            self.connection.quit(msg)

    def on_welcome(self, c, e):
        logger.debug("Joining {self.channel}")

        # You must request specific capabilities before you can use them
        c.join(self.channel)
        c.cap('REQ', ':twitch.tv/membership')
        c.cap('REQ', ':twitch.tv/tags')
        c.cap('REQ', ':twitch.tv/commands')
        c.privmsg(self.channel, "/me ist bereit")
        self.ready.set()

    def on_pubmsg(self, c, e):
        if e.arguments[0][:1] == self.prefix:
            cmd = e.arguments[0].split(' ')
            command = cmd[0][1:].lower()

            if command in self.command_everyone:
                self.do_command(None, (command, cmd[1:]))

                return

            user = User()

            for tag in e.tags:
                if tag['key'] == 'display-name':
                    user.name = tag['value'].lower()
                    user.broadcaster = True if user.name == self.channel[1:] else False
                elif tag['key'] == 'mod' and tag['value'] == '1':
                    user.mod = True
                elif tag['key'] == 'subscriber' and tag['value'] == '1':
                    user.sub = True
                elif tag['key'] == 'user-id':
                    user.id = tag['value']

            if user.name not in self.authorize_user and not (self.authorize_mods and user.mod) and not user.broadcaster:
                return

            self.do_command(user, (command, cmd[1:]))

    def do_command(self, user, cmd):
        try:
            command = self.commands[cmd[0]]
            asyncio.run_coroutine_threadsafe(command(args=cmd[1]), self.loop)
        except KeyError:
            logger.debug(f"Unknown command !{cmd[0]}")

    def add_command(self, name, callback):
        self.commands[name] = callback

    def send(self, text):
        self.connection.privmsg(self.channel, text)
