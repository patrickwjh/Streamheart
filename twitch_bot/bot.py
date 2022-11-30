# -*- coding: utf-8 -*-

import time
import signal
import asyncio
import logging
from pathlib import Path
from functools import partial
from configparser import ConfigParser
from twitch_bot import irc_bot
from misc import baseclient, exceptions, message as msg

APPLICATION_NAME = 'TwitchBot'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 4445
DEFAULT_CONFIG_PATH = f"{str(Path.home())}/.config/Streamheart/twitch_bot/TwitchBot.json"
DEFAULT_STREAMHEART_CONFIG_PATH = f"{str(Path.home())}/.config/Streamheart/Streamheart.conf"

logger = logging.getLogger(__name__)
bot_config = DEFAULT_CONFIG_PATH
streamheart_config = DEFAULT_STREAMHEART_CONFIG_PATH
middleware_host = DEFAULT_HOST
middleware_port = DEFAULT_PORT
start_scene = None
brb_scene = None
live_scene = None
end_scene = None
stream_source = None
overlay_source = None
main_collection = None
refresh_collection = None
screenshot_path = None
current_scene = None
map_source = None


async def command_screenshot(bot, client, args=None):
    try:
        await client.send_wait(
            msg.Request('OBS Studio', 'TakeSourceScreenshot', client.message_manager.new_id(),
                        **{'sourceName': stream_source,
                           'saveToFilePath': f"{screenshot_path}{time.strftime('%Y-%m-%d_%H-%M-%S')}.jpg"}))
    except exceptions.RequestTimeout as error:
        logger.debug(f"Request timeout. message-id: {error.message_id}")
        bot.send("Sorry, etwas ist schief gelaufen. Starte Streamheart neu")
    except exceptions.ResponseStatusError as error:
        logger.debug(f"{error}. message-id: {error.message_id}")
        bot.send(f"!screenshot {error}")


async def command_refresh(bot, client, args=None):
    try:
        if args:
            if args[0] == 'overlay':
                await client.send_wait(
                    msg.Request('OBS Studio', 'SetSceneItemProperties', client.message_manager.new_id(),
                                **{'item': overlay_source, 'visible': False}))
                await asyncio.sleep(1)
                await client.send_wait(
                    msg.Request('OBS Studio', 'SetSceneItemProperties', client.message_manager.new_id(),
                                **{'item': overlay_source, 'visible': True}))
        else:
            await client.send_wait(msg.Request('OBS Studio', 'SetCurrentSceneCollection',
                                               client.message_manager.new_id(), **{'sc-name': refresh_collection}))
            await asyncio.sleep(1)
            await client.send_wait(msg.Request('OBS Studio', 'SetCurrentSceneCollection',
                                               client.message_manager.new_id(), **{'sc-name': main_collection}))
    except exceptions.RequestTimeout as error:
        logger.debug(f"Request timeout. message-id: {error.message_id}")
        bot.send("Sorry, etwas ist schief gelaufen. Starte Streamheart neu")
    except exceptions.ResponseStatusError as error:
        logger.debug(f"{error}. message-id: {error.message_id}")
        bot.send(f"!refresh {args[0] if args else ''} hat nicht geklappt")


async def command_stream(bot, client, args=None):
    try:
        if args:
            if args[0] == 'start':
                await client.send_wait(msg.Request('OBS Studio', 'SetCurrentScene', client.message_manager.new_id(),
                                                   **{'scene-name': start_scene}))
                await client.send_wait(msg.Request(
                    'OBS Studio', 'StartStreaming', client.message_manager.new_id(), **{'scene-name': start_scene}))
            elif args[0] == 'stop':
                await client.send_wait(msg.Request(
                    'OBS Studio', 'StopStreaming', client.message_manager.new_id(), **{'scene-name': start_scene}))
    except exceptions.RequestTimeout as error:
        logger.debug(f"Request timeout. message-id: {error.message_id}")
        bot.send("Sorry, etwas ist schief gelaufen. Starte Streamheart neu")
    except exceptions.ResponseStatusError as error:
        logger.debug(f"{error}. message-id: {error.message_id}")
        bot.send(f"!stream {args[0] if args else ''} hat nicht geklappt")


async def command_start(bot, client, args=None):
    try:
        if start_scene:
            await client.send_wait(msg.Request('OBS Studio', 'SetCurrentScene', client.message_manager.new_id(),
                                               **{'scene-name': start_scene}))
    except exceptions.RequestTimeout as error:
        logger.debug(f"Request timeout. message-id: {error.message_id}")
        bot.send("Sorry, etwas ist schief gelaufen. Starte Streamheart neu")
    except exceptions.ResponseStatusError as error:
        logger.debug(f"{error}. message-id: {error.message_id}")
        bot.send("!start hat nicht geklappt")


async def command_end(bot, client, args=None):
    try:
        if start_scene:
            await client.send_wait(msg.Request('OBS Studio', 'SetCurrentScene', client.message_manager.new_id(),
                                               **{'scene-name': end_scene}))
    except exceptions.RequestTimeout as error:
        logger.debug(f"Request timeout. message-id: {error.message_id}")
        bot.send("Sorry, etwas ist schief gelaufen. Starte Streamheart neu")
    except exceptions.ResponseStatusError as error:
        logger.debug(f"{error}. message-id: {error.message_id}")
        bot.send("!end hat nicht geklappt")


async def command_live(bot, client, args=None):
    try:
        await client.send_wait(msg.Request('OBS Studio', 'SetCurrentScene', client.message_manager.new_id(),
                                           **{'scene-name': live_scene}))
    except exceptions.RequestTimeout as error:
        logger.debug(f"Request timeout. message-id: {error.message_id}")
        bot.send("Sorry, etwas ist schief gelaufen. Starte Streamheart neu")
    except exceptions.ResponseStatusError as error:
        logger.debug(f"{error}. message-id: {error.message_id}")
        bot.send("!live hat nicht geklappt")


async def command_low(bot, client, args=None):
    if args:
        try:
            low_bitrate = int(args[0])
            await client.send_wait(msg.Request(
                'Heartrate', 'SetLowLimit', client.message_manager.new_id(), limit=low_bitrate))
            bot.send(f"Bitrate wurde auf {low_bitrate} kbps gesetzt")
        except ValueError:
            logger.debug("Invalid low argument")
        except exceptions.RequestTimeout as error:
            logger.debug(f"Request timeout. message-id: {error.message_id}")
            bot.send("Sorry, etwas ist schief gelaufen. Starte Streamheart neu")
        except exceptions.ResponseStatusError as error:
            logger.debug(f"{error}. message-id: {error.message_id}")
            bot.send(f"!low {args[0] if args else ''} hat nicht geklappt")


async def command_brb(bot, client, args=None):
    try:
        if args:
            if args[0] == 'on':
                await client.send_wait(msg.Request('Heartrate', 'EnableBrb', client.message_manager.new_id()))
                bot.send("Auto BRB: AN")
            elif args[0] == 'off':
                await client.send_wait(msg.Request('Heartrate', 'DisableBrb', client.message_manager.new_id()))
                bot.send("Auto BRB: AUS")
            else:
                try:
                    brb_bitrate = int(args[0])
                    await client.send_wait(msg.Request(
                        'Heartrate', 'SetBrbLimit', client.message_manager.new_id(), limit=brb_bitrate))
                    bot.send(f"Bitrate wurde auf {brb_bitrate} kbps gesetzt")
                except ValueError:
                    logger.debug("Invalid brb argument")
        else:
            await client.send_wait(msg.Request('OBS Studio', 'SetCurrentScene',
                                               client.message_manager.new_id(), **{'scene-name': brb_scene}))
    except exceptions.RequestTimeout as error:
        logger.debug(f"Request timeout. message-id: {error.message_id}")
        bot.send("Sorry, etwas ist schief gelaufen. Starte Streamheart neu")
    except exceptions.ResponseStatusError as error:
        logger.debug(f"{error}. message-id: {error.message_id}")
        bot.send(f"!brb {args[0] if args else ''} hat nicht geklappt")


async def command_bitrate(bot, client, args=None):
    try:
        response = await client.send_wait(msg.Request('Heartrate', 'GetBitrate', client.message_manager.new_id()))
        bitrate = response.additionals['bitrate'] // 1000
        if bitrate == 0:
            bot.send(f"Aktuelle Bitrate: OFFLINE")
        else:
            bot.send(f"Aktuelle Bitrate: {bitrate} kbps")
    except exceptions.RequestTimeout as error:
        logger.debug(f"Request timeout. message-id: {error.message_id}")
        bot.send("Sorry, etwas ist schief gelaufen. Starte Streamheart neu")
    except exceptions.ResponseStatusError as error:
        logger.debug(f"{error}. message-id: {error.message_id}")
        bot.send("Die Bitrate ist unbekannt")


async def command_position(bot, client, args=None):
    try:
        await client.subscribe('WebApp', loop=False)

        if args:
            pass
        else:
            await client.send(msg.Request('WebApp', 'GetPosition', client.message_manager.new_id()))

    except exceptions.SubscribeException:
        await client.send(msg.Request('WebApp', 'GetPosition', client.message_manager.new_id()))


async def event_switch_scenes(message, client, bot):
    global current_scene

    scene = message.additionals['scene-name']

    if scene != current_scene:
        bot.send(f"Szene wechselt zu {scene}")
        current_scene = scene


async def event_status_changed(message, client, bot):
    status = message.additionals['stream_status']

    if status == 'OFFLINE':
        bot.send("Verbindung verloren. Bitrate: OFFLINE")
    elif status == 'CRITICAL':
        bot.send(f"Schlechte Verbindung. Bitrate: {message.additionals['bitrate'] // 1000} kbps")
    elif status == 'LOW':
        bot.send(f"Bitrate: {message.additionals['bitrate'] // 1000} kbps")
    elif status == 'STABLE':
        bot.send(f"Bitrate: {message.additionals['bitrate'] // 1000} kbps")


async def event_current_position(message, client, bot):
    latitude = message.additionals.get('latitude')
    longitude = message.additionals.get('longitude')
    error = message.additionals.get('error')

    if latitude and longitude:
        bot.send(f"https://www.google.com/maps/search/?api=1&query={latitude}%2C{longitude}")
        try:
            await client.send_wait(
                msg.Request('OBS Studio', 'SetSceneItemProperties', client.message_manager.new_id(),
                            **{'item': map_source, 'visible': True}))
            await asyncio.sleep(8)
            await client.send_wait(
                msg.Request('OBS Studio', 'SetSceneItemProperties', client.message_manager.new_id(),
                            **{'item': map_source, 'visible': False}))
        except exceptions.RequestTimeout as error:
            logger.debug(f"Request timeout. message-id: {error.message_id}")
        except exceptions.ResponseStatusError as error:
            logger.debug(f"{error}. message-id: {error.message_id}")
    elif error:
        bot.send(str(error))


async def event_unsubscribed_from(message, client, bot):
    app = message.additionals['name']

    if app != 'WebApp':
        asyncio.create_task(client.subscribe(message.additionals['name']))


def load_streamheart_config():
    global start_scene, brb_scene, live_scene, end_scene, \
        main_collection, refresh_collection, overlay_source, stream_source, screenshot_path, map_source

    try:
        config = ConfigParser()
        config.read(streamheart_config)
        obs_section = config['OBS']

        start_scene = obs_section['start_scene_name']
        brb_scene = obs_section['brb_scene_name']
        live_scene = obs_section['live_scene_name']
        end_scene = obs_section['end_scene_name']
        main_collection = obs_section['main_scene_collection']
        refresh_collection = obs_section['clear_scene_collection']
        overlay_source = obs_section['overlay_source_name']
        stream_source = obs_section['stream_source_name']
        map_source = obs_section['map_source_name']
    except KeyError as error:
        logger.error(f"Config error: Can't find {error}")
        raise


async def start(streamheart_config_path=DEFAULT_STREAMHEART_CONFIG_PATH, bot_config_path=DEFAULT_CONFIG_PATH,
                host=DEFAULT_HOST, port=DEFAULT_PORT, ssl_cert=None):
    global bot_config, streamheart_config, middleware_host, middleware_port

    streamheart_config = streamheart_config_path if streamheart_config_path else DEFAULT_STREAMHEART_CONFIG_PATH
    bot_config = bot_config_path if bot_config_path else DEFAULT_CONFIG_PATH
    middleware_host, middleware_port = host if host else DEFAULT_HOST, port if port else DEFAULT_PORT

    try:
        load_streamheart_config()
    except KeyError:
        return

    loop = asyncio.get_running_loop()

    # Twitch chat bot
    bot = irc_bot.Bot(bot_config, loop)

    # Websocket to heart
    subscriptions = ['OBS Studio', 'Heartrate']
    client = baseclient.Client('twitch_bot', (DEFAULT_HOST, DEFAULT_PORT), APPLICATION_NAME, subscriptions, ssl_cert)
    client.add_event('SwitchScenes', partial(event_switch_scenes, client=client, bot=bot))
    client.add_event('StatusChanged', partial(event_status_changed, client=client, bot=bot))
    client.add_event('CurrentPosition', partial(event_current_position, client=client, bot=bot))
    client.add_event('UnsubscribedFrom', partial(event_unsubscribed_from, client=client, bot=bot))

    bot.add_command('bitrate', partial(command_bitrate, bot=bot, client=client))
    bot.add_command('brb', partial(command_brb, bot=bot, client=client))
    bot.add_command('low', partial(command_low, bot=bot, client=client))
    bot.add_command('live', partial(command_live, bot=bot, client=client))
    bot.add_command('start', partial(command_start, bot=bot, client=client))
    bot.add_command('end', partial(command_end, bot=bot, client=client))
    bot.add_command('stream', partial(command_stream, bot=bot, client=client))
    bot.add_command('refresh', partial(command_refresh, bot=bot, client=client))
    bot.add_command('screenshot', partial(command_screenshot, bot=bot, client=client))
    bot.add_command('position', partial(command_position, bot=bot, client=client))

    client_task = asyncio.create_task(client.connect())

    loop.add_signal_handler(signal.SIGTERM, partial(stop, client_task, bot))
    loop.add_signal_handler(signal.SIGINT, partial(stop, client_task, bot))

    bot_start = loop.run_in_executor(None, bot.start)

    try:
        done, pending = await asyncio.wait([bot_start, client_task], return_when=asyncio.FIRST_COMPLETED)

        if bot_start in pending:
            bot.die()

        [future.cancel() for future in pending]
        [future.exception() for future in done]
    except asyncio.CancelledError:
        logger.debug(f"{client.name} stopped")
    except exceptions.ReconnectTimeout:
        logger.error(f"{client.name} reached maximum reconnects")


def stop(task, bot):
    task.cancel()
    bot.die()
