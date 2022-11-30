# -*- coding: utf-8 -*-

import signal
import asyncio
import logging
from pathlib import Path
from functools import partial
from heart_rate import stream_bitrate
from configparser import ConfigParser
from misc import baseclient, exceptions, message as msg

APPLICATION_NAME = 'Heartrate'
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 4445
DEFAULT_CONFIG_PATH = f"{str(Path.home())}/.config/Streamheart/Streamheart.conf"

logger = logging.getLogger(__name__)
streamheart_config = DEFAULT_CONFIG_PATH
middleware_host = DEFAULT_HOST
middleware_port = DEFAULT_PORT
brb_scene = None
live_scene = None
current_scene = None
bad_connection = None
auto_brb = True


async def request_get_bitrate(message, client, stream):
    try:
        bitrate = stream.stream['bitrate']
        await client.send(msg.Ok(message.id, bitrate=bitrate, stream_status=stream.get_health_state()))
    except KeyError:
        await client.send(msg.Ok(message.id, bitrate=0, stream_status=stream.get_health_state()))


async def request_disable_brb(message, client, stream):
    stream.active.clear()
    stream.health.status.update(stream_bitrate.stream_health.State.OFFLINE)
    await client.send(msg.Ok(message.id))
    await client.send(msg.Event('BrbDisabled'))


async def request_enable_brb(message, client, stream):
    stream.active.set()
    stream.health.status.update(stream_bitrate.stream_health.State.OFFLINE)
    await client.send(msg.Ok(message.id))
    await client.send(msg.Event('BrbEnabled'))


async def request_get_brb_status(message, client, stream):
    if stream.active.is_set():
        await client.send(msg.Ok(message.id, enabled=True))
    else:
        await client.send(msg.Ok(message.id, enabled=False))


async def request_set_brb_limit(message, client, stream):
    config = ConfigParser()
    config.read(streamheart_config)

    try:
        heartrate_section = config['HEARTRATE']

        with open(streamheart_config, 'w') as configfile:
            stream.critical_bitrate = message.additionals['limit'] * 1000
            heartrate_section['BRB_BITRATE'] = str(message.additionals['limit'])
            config.write(configfile)
            await client.send(msg.Ok(message.id))
    except OSError as error:
        logger.debug(f"Can't set brb limit. {error.strerror}")
        await client.send(msg.Error("Can't change bitrate limit for BRB"), message.id)
    except KeyError:
        logger.debug(f"Can't set brb limit. Config error")
        await client.send(msg.Error("Can't change bitrate limit for BRB", message.id))


async def request_set_low_limit(message, client, stream):
    config = ConfigParser()
    config.read(streamheart_config)

    try:
        heartrate_section = config['HEARTRATE']

        with open(streamheart_config, 'w') as configfile:
            stream.low_bitrate = message.additionals['limit'] * 1000
            heartrate_section['LOW_BITRATE'] = str(message.additionals['limit'])
            config.write(configfile)
            await client.send(msg.Ok(message.id))
    except OSError as error:
        logger.debug(f"Can't set low limit. {error.strerror}")
        await client.send(msg.Error("Can't change bitrate limit for LOW"), message.id)
    except KeyError:
        logger.debug(f"Can't set low limit. Config error")
        await client.send(msg.Error("Can't change bitrate limit for LOW", message.id))


async def event_switch_scenes(message, client, stream):
    global current_scene, auto_brb

    current_scene = message.additionals['scene-name']

    if current_scene != live_scene and (stream.get_health_state() is
                                        stream_bitrate.stream_health.State.STABLE or stream.get_health_state() is
                                        stream_bitrate.stream_health.State.LOW):
        auto_brb = False
        logger.debug("Auto-BRB OFF")
    else:
        auto_brb = True
        logger.debug("Auto-BRB ON")

    logger.debug(f"CurrentScene: {current_scene}, state: {stream.get_health_state()}")


async def event_unsubscribed_from(message, client, stream):
    asyncio.create_task(client.subscribe(message.additionals['name']))


async def check_scenes(client):
    await client.ready.wait()
    try:
        global brb_scene, live_scene, current_scene, bad_connection

        response = await client.send_wait(msg.Request('OBS Studio', 'GetSceneList', client.message_manager.new_id()))
        current_scene = response.additionals['current-scene']
        scenes = response.additionals['scenes']
        scene_names = (scene['name'] for scene in scenes)
        config = ConfigParser()
        config.read(streamheart_config)
        obs_section = config['OBS']

        brb_scene = obs_section['brb_scene_name']
        live_scene = obs_section['live_scene_name']
        bad_connection = obs_section['bad_connection_source_name']

        if brb_scene not in scene_names and live_scene not in scene_names:
            raise exceptions.ConfigError(
                f"Scene names in config doesn't match OBS scene names")
    except exceptions.RequestTimeout as error:
        logger.debug(f"Request timeout. message-id: {error.message_id}")
    except exceptions.ResponseStatusError as error:
        logger.debug(f"{error}. message-id: {error.message_id}")
    except KeyError as error:
        logger.error(f"Config error: Can't find {error}")
        raise


async def run_check_health(client, stream):
    current_state = stream.get_health_state()
    states = stream_bitrate.stream_health.State

    while True:
        await client.ready.wait()
        state = await stream.check_health()

        if not stream.active.is_set():
            current_state = stream.get_health_state()
            continue

        if state is states.ERROR:
            continue

        if not auto_brb:
            logger.debug("Continue. Auto-BRB False")
            continue

        if state is not current_state:
            try:
                if (state is states.OFFLINE or state is states.CRITICAL) and \
                        (current_state is not states.OFFLINE or current_state is not states.CRITICAL):
                    if state is states.LOW and bad_connection:
                        await client.send_wait(
                            msg.Request('OBS Studio', 'SetSceneItemProperties', client.message_manager.new_id(),
                                        **{'item': bad_connection, 'visible': False}))

                    await client.send_wait(msg.Request('OBS Studio', 'SetCurrentScene', client.message_manager.new_id(),
                                                       **{'scene-name': brb_scene}))
                elif state is states.LOW:
                    if current_scene != live_scene:
                        await client.send_wait(msg.Request('OBS Studio', 'SetCurrentScene',
                                                           client.message_manager.new_id(),
                                                           **{'scene-name': live_scene}))
                    if bad_connection:
                        await client.send_wait(
                            msg.Request('OBS Studio', 'SetSceneItemProperties', client.message_manager.new_id(),
                                        **{'item': bad_connection, 'visible': True}))
                elif state is states.STABLE:
                    if current_scene != live_scene:
                        await client.send_wait(msg.Request('OBS Studio', 'SetCurrentScene',
                                                           client.message_manager.new_id(),
                                                           **{'scene-name': live_scene}))
                    if bad_connection:
                        await client.send_wait(
                            msg.Request('OBS Studio', 'SetSceneItemProperties', client.message_manager.new_id(),
                                        **{'item': bad_connection, 'visible': False}))
            except exceptions.RequestTimeout as error:
                logger.debug(f"Request timeout. message-id: {error.message_id}")
            except exceptions.ResponseStatusError as error:
                logger.debug(f"{error}. message-id: {error.message_id}")

            await client.send(msg.Event('StatusChanged', stream_status=state, bitrate=stream.stream['bitrate']))
            current_state = state


async def start(config_path=DEFAULT_CONFIG_PATH, host=DEFAULT_HOST, port=DEFAULT_PORT, ssl_cert=None):
    global streamheart_config, middleware_host, middleware_port

    streamheart_config = config_path if config_path else DEFAULT_CONFIG_PATH
    middleware_host, middleware_port = host if host else DEFAULT_HOST, port if port else DEFAULT_PORT
    loop = asyncio.get_event_loop()

    # Bitrate stream
    stream = stream_bitrate.StreamBitrate(streamheart_config)

    # Websocket to heart
    subscriptions = ['OBS Studio']
    client = baseclient.Client('heart_rate', (middleware_host, middleware_port), APPLICATION_NAME, subscriptions,
                               ssl_cert)
    client.add_event('SwitchScenes', partial(event_switch_scenes, client=client, stream=stream))
    client.add_event('UnsubscribedFrom', partial(event_unsubscribed_from, client=client, stream=stream))
    client.add_request('GetBitrate', partial(request_get_bitrate, client=client, stream=stream))
    client.add_request('DisableBrb', partial(request_disable_brb, client=client, stream=stream))
    client.add_request('EnableBrb', partial(request_enable_brb, client=client, stream=stream))
    client.add_request('GetBrbStatus', partial(request_get_brb_status, client=client, stream=stream))
    client.add_request('SetBrbLimit', partial(request_set_brb_limit, client=client, stream=stream))
    client.add_request('SetLowLimit', partial(request_set_low_limit, client=client, stream=stream))

    conncect_task = asyncio.create_task(client.connect())
    check_task = asyncio.create_task(check_scenes(client))
    loop.add_signal_handler(signal.SIGTERM, partial(stop, [conncect_task, check_task]))
    loop.add_signal_handler(signal.SIGINT, partial(stop, [conncect_task, check_task]))

    try:
        await check_task
        health_task = asyncio.create_task(run_check_health(client, stream))

        loop.remove_signal_handler(signal.SIGTERM)
        loop.remove_signal_handler(signal.SIGINT)
        loop.add_signal_handler(signal.SIGTERM, partial(stop, [conncect_task, health_task]))
        loop.add_signal_handler(signal.SIGINT, partial(stop, [conncect_task, health_task]))

        done, pending = await asyncio.wait([health_task, conncect_task], return_when=asyncio.FIRST_COMPLETED)
        [future.cancel() for future in pending]
        [future.exception() for future in done]
    except asyncio.CancelledError:
        logger.debug(f"{client.name} stopped")
    except exceptions.ReconnectTimeout:
        logger.error(f"{client.name} reached maximum reconnects")
    except exceptions.ConfigError as error:
        logger.error(error)
    except KeyError as error:
        logger.debug(f"KeyError: {error}")
    finally:
        stream.stop()


def stop(tasks):
    [task.cancel() for task in tasks]
