# -*- coding: utf-8 -*-

import os
import signal
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def check_log_file(path):
    try:
        if not os.path.exists(path):
            open(path, 'x').close()
    except OSError as error:
        logger.error(f"Can't create {path}. {error.strerror}")
        return False
    return True


def read_pid_file(path):
    with open(path, 'r') as file:
        return int(file.readline())


def remove_pid_file(path):
    try:
        os.remove(path)
    except OSError as error:
        logger.error(f"Can't remove {path} ({error.strerror})")
        return False
    return True


def check_pid_running(path, pid=None):
    try:
        if pid:
            os.kill(pid, 0)
        else:
            os.kill(read_pid_file(path), 0)
    except OSError:
        return False

    return True


def run(application_name, callback, arguementparser):
    log_path = f'{str(Path.home())}/.config/Streamheart/logs/{application_name}.log'
    pid_path = f'{str(Path.home())}/.config/Streamheart/{application_name}/{application_name}.pid'
    args = arguementparser.parse_args()

    if args.debug:
        websockets_logger = logging.getLogger('websockets')
        websockets_logger.setLevel(logging.INFO)
        logging.basicConfig(level=logging.DEBUG)
    else:
        if not check_log_file(log_path):
            exit(1)
        logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                            datefmt='%Y/%m/%d %H:%M:%S')

    if args.signal == 'stop':
        if not os.path.exists(pid_path):
            logger.info(f"Stopping {application_name}: {application_name} isn't running")
            exit(1)
        else:
            pid = read_pid_file(pid_path)

            if check_pid_running(pid_path, pid=pid):
                os.kill(pid, signal.SIGTERM)
                logger.info(f"Stopping {application_name}: {application_name} stopped")
            else:
                logger.info(
                    f"{application_name}.pid exist but process isn't running. Removing obsolete {application_name}.pid")
                if not remove_pid_file(pid_path):
                    exit(1)
            exit(0)

    if os.path.exists(pid_path):
        if not check_pid_running(pid_path):
            logger.info(
                f"{application_name}.pid exist but process isn't running. Removing obsolete {application_name}.pid")
            if not remove_pid_file(pid_path):
                exit(1)
        else:
            logger.info(f"{application_name} is already running: PID {read_pid_file(pid_path)}")
            exit(1)

    try:
        with open(pid_path, 'x') as pid_file:
            pid_file.write(str(os.getpid()))
    except OSError as error:
        logger.error(f"Can't create {application_name}.pid ({error.strerror})")
        exit(1)

    logger.info(f"{application_name} started")

    if not args.debug:
        logging.basicConfig(level=logging.ERROR)

    callback()

    if not args.debug:
        logging.basicConfig(level=logging.INFO)

    logger.info(f"{application_name} closed")

    remove_pid_file(pid_path)
