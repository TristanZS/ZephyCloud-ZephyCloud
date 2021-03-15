#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: set tabstop=4:softtabstop=4:shiftwidth=4:expandtab:textwidth=120

# Python core api
import sys
import logging
import logging.handlers
import os
import time
import datetime
import argparse
import re
import multiprocessing
import signal
import subprocess

# Third party libraries
import colorlog
import watchdog.events
import watchdog.observers

# Project specific libs
from lib import util
from lib import type_util
from lib import proc_util
from lib import async_util
from lib import redis_util
from lib import error_util
from lib import debug_util
import models.jobs
import models.projects
import models.meshes
import models.calc
import models.provider_config
import models.currencies
import core.api_util


# constants:
REDIS_MESSAGE = 1
SRC_CHANGED_MESSAGE = 2

API_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

log = logging.getLogger("aziugo")
CANCEL_JOB_TIMEOUT = 300
IGNORE_SIGNAL_DELAY = datetime.timedelta(milliseconds=500)
GC_ENABLED = True


class RedisReceiver(async_util.AbstractThread):
    def __init__(self, msg_queue, api_name, server_name, *args, **kwargs):
        """
        :param msg_queue:       FIFO queue where we put received messages
        :type msg_queue:        Queue.Queue
        :param api_name:        The name of current API
        :type api_name:         str
        """
        super(RedisReceiver, self).__init__(*args, **kwargs)
        self._msg_queue = msg_queue
        self._api_name = api_name
        self._server_name = server_name

    def work(self, *args, **kwargs):
        try:
            core.api_util.wait_for_redis()

            with core.api_util.RedisContext.using_pubsub_conn() as redis_conn:
                channel = core.api_util.RedisContext.get_channel("launcher")
                for message in redis_util.listen_pubsub(redis_conn, channel, datetime.timedelta(seconds=1)):
                    if self.should_stop():
                        return
                    if message is None:
                        continue
                    if not re.match(r"^.*_\d+$", message['data']):
                        log.warning(message['data'] + ' format is invalid')
                        continue
                    task, jobid_str = message['data'].rsplit('_', 1)
                    self._msg_queue.put({'type': REDIS_MESSAGE, "data": {
                        'task': task,
                        'jobid': int(jobid_str)
                    }})
        except StandardError as e:
            error_util.log_error(log, e)


class PriceBurner(async_util.RecurringThread):
    @property
    def delay(self):
        return datetime.timedelta(days=1)

    def work(self, *args, **kwargs):
        try:
            if self.should_stop():
                return
            now = datetime.datetime.utcnow()
            last_charge_limit = now - datetime.timedelta(minutes=1)
            # FIXME: Disable because it lock the database: with core.api_util.DatabaseContext.using_conn():
            models.projects.charge_all(last_charge_limit)
            models.meshes.charge_all(last_charge_limit)
            models.calc.charge_all(last_charge_limit)
        except StandardError as e:
            error_util.log_error(log, e)


class PriceUpdater(async_util.RecurringThread):
    @property
    def delay(self):
        return datetime.timedelta(days=7)

    def work(self, *args, **kwargs):
        try:
            if self.should_stop():
                return

            conf = core.api_util.get_conf()
            currency_api_url = conf.get("currency", "currency_api_url")
            if type_util.is_array(currency_api_url):
                log.warning("This should not be a list: "+repr(currency_api_url))
                currency_api_url = "".join(currency_api_url)
            currency_api_token = conf.get("currency", "currency_api_token")
            aws_pricing_api = conf.get("general", "provider_pricing_api")

            # FIXME: Disable because it lock the database: with core.api_util.DatabaseContext.using_conn():
            models.currencies.update_currency_exchange_rates(currency_api_url, currency_api_token)
            if self.should_stop():
                return
            for provider in core.api_util.get_all_providers():
                if self.should_stop():
                    return
                models.provider_config.update_provider_costs(aws_pricing_api, provider.name)
            models.provider_config.update_machine_prices()
        except StandardError as e:
            error_util.log_error(log, e)


def compute_variance(data):
    y_squared_dot = sum(i * i for i in data)
    y_dot_squared = sum(data) ** 2
    return (y_squared_dot - y_dot_squared / len(data)) / (len(data) - 1)


class SpotIndexUpdater(async_util.RecurringThread):
    def __init__(self, provider, *args, **kwargs):
        super(SpotIndexUpdater, self).__init__(*args, **kwargs)
        self._provider = provider

    @property
    def delay(self):
        return datetime.timedelta(minutes=10)

    def work(self, *args, **kwargs):
        try:
            # FIXME: Disable because it lock the database: with core.api_util.DatabaseContext.using_conn():
            for machine in models.provider_config.list_machines(self._provider.name):
                if self.should_stop():
                    return
                cost = models.provider_config.get_machine_provider_cost(self._provider.name,
                                                                        machine['machine_code'])
                cost = core.api_util.price_to_float(int(cost['cost_per_sec'])*3600)
                prices = async_util.run_proc(SpotIndexUpdater.load_prices, self._provider.name,
                                             machine['machine_code'])
                if not prices:
                    log.error("No price history found for machine "+str(machine['machine_code']))
                    continue
                price_variance = compute_variance(prices)
                price_max = max(prices)
                index = max(0, ((price_max - abs(price_variance))/price_max) - (max(0, cost - price_max)/cost)**10)
                models.provider_config.set_spot_index(self._provider.name, machine['machine_code'], index)
        except error_util.all_errors as e:
            error_util.log_error(log, e)

    @staticmethod
    def load_prices(provider_name, machine_code):
        provider = core.api_util.get_provider(provider_name)
        return provider.get_spot_price_history(machine_code)


class SrcCodeEventHandler(watchdog.events.PatternMatchingEventHandler):
    """
    This class waits for source code changes and launch event
    """
    def __init__(self, queue):
        """
        :param queue:       FIFO queue where we put messages when source code changes
        :type queue:        Queue.Queue
        """
        super(SrcCodeEventHandler, self).__init__(ignore_patterns=["*.pyc"])
        self._queue = queue
        self._detected = False

    def on_any_event(self, event):
        """
        This method is called when a file changed.
        It send event into the queue

        :param event:           The file changed event
        :type event:            watchdog.events.FileSystemEvent
        """
        if not self._detected:
            log.info("Code change detected")
        self._detected = True
        self._queue.put({'type': SRC_CHANGED_MESSAGE, "data": None})


class SourceChangeNotifier(async_util.AbstractThread):
    """ Listen to source code changes """

    def __init__(self, msg_queue, *args, **kwargs):
        """
        :param msg_queue:       FIFO queue where we put received messages
        :type msg_queue:        Queue.Queue
        """
        super(SourceChangeNotifier, self).__init__(*args, **kwargs)
        self._msg_queue = msg_queue

    def work(self, *args, **kargs):
        try:
            time.sleep(5)  # Don't start immediately
            evt_handler = SrcCodeEventHandler(self._msg_queue)
            observer = watchdog.observers.Observer()
            observer.schedule(evt_handler, os.path.join(API_PATH, "app"), recursive=True)
            observer.start()
            self.wait_for_stop()
            observer.stop()
            observer.join()
        except StandardError as e:
            error_util.log_error(log, e)


def run_task(api_name, server_name, task_order, job_id, log_level, log_output):
    """
    Execute a task, which could be to cancel a running toolchain or to launch a specific toolchain.
    It will launch a separated subprocess and return before task is completed

    :param api_name:            The name of current API
    :type api_name:             str
    :param server_name:         The fqdn of current server
    :type server_name:          str
    :param task_order:          The task to do (launch or cancel)
    :type task_order:           int
    :param job_id:              The is of the job the task is related to
    :type job_id:               int
    :param log_level:           The level of log we want
    :type log_level:            int
    :param log_output:          Where do we should output the logs. Should be "stdout", "stderr", "syslog" or a file
    :type log_output:           str
    """

    if task_order == models.jobs.TASK_CANCEL:
        models.jobs.dequeue_task(job_id)
        proc = multiprocessing.Process(target=cancel_job, args=(api_name, server_name, job_id,))
        proc.daemon = True
        proc.start()
    elif task_order in [models.jobs.TASK_UPLOAD_AND_ANALYSE, models.jobs.TASK_UPLOAD_AND_LINK,
                        models.jobs.TASK_MESH, models.jobs.TASK_CALC, models.jobs.TASK_RESTART_CALC]:
        try:
            # The task will be dequeued by the process to get the task parameters
            subprocess.check_call(["python",
                                   os.path.join(API_PATH, "app", "run_job.py"),
                                   "--fork",
                                   "--log-level", logging.getLevelName(log_level),
                                   "--log-output", log_output,
                                   '--redis-host', core.api_util.RedisContext.get_host(),
                                   '--redis-port', str(core.api_util.RedisContext.get_port()),
                                   '--redis-data-db', str(core.api_util.RedisContext.get_data_db()),
                                   '--redis-pubsub-db', str(core.api_util.RedisContext.get_pubsub_db()),
                                   str(job_id),
                                   str(task_order)])
        except core.api_util.abort_errors:
            models.jobs.dequeue_task(job_id)
            log.warning("Operation canceled")
            models.jobs.set_job_status(job_id, models.jobs.JOB_STATUS_CANCELED)
        except core.api_util.ToolchainError as e:
            models.jobs.dequeue_task(job_id)
            log.error(str(e))
            models.jobs.set_job_status(job_id, models.jobs.JOB_STATUS_KILLED)
        except error_util.all_errors as e:
            models.jobs.dequeue_task(job_id)
            error_util.log_error(log, e)
            models.jobs.set_job_status(job_id, models.jobs.JOB_STATUS_KILLED)
    else:
        models.jobs.dequeue_task(job_id)
        log.error("Task not implemented: " + str(task_order))
        return


@core.api_util.need_db_context
def cancel_job(api_name, server_name, job_id):
    """
    Cancel a running job.
    It will mark the job as canceled, send signal to actual running process and finally
    kill it if the process is stuck for too long

    :param api_name:            The name of current API
    :type api_name:             str
    :param server_name:         The name of current server
    :type server_name:          str
    :param job_id:              The job to stop
    :type job_id:               int
    """
    log.info("Order to cancel job "+str(job_id)+" received")
    models.jobs.set_job_status(job_id, models.jobs.JOB_STATUS_CANCELED)
    with core.api_util.RedisContext.using_data_conn() as r:
        pid = r.get(api_name+":"+server_name+":job-" + str(job_id) + "-pid")
    if not pid:
        log.info("No job " + str(job_id) + " detected, skipping cancel")
        return
    if not proc_util.is_process_running(pid):
        log.info("Process is not running (pid = "+str(pid)+")")
        return
    log.info("Stopping job " + str(job_id) + ": sending message to process "+str(pid))
    if not proc_util.ensure_stop_proc(pid, CANCEL_JOB_TIMEOUT):
        log.warning("Process for job " + str(job_id) + " didn't stop properly after " +
                    str(CANCEL_JOB_TIMEOUT)+" seconds, we killed it")


def run_pending_jobs(api_name, server_name, log_level, log_output):
    """
    Run all pending jobs. It is useful at script startup or when redis server is down.

    :param api_name:            The name of current API
    :type api_name:             str
    :param server_name:         The name of current server
    :type server_name:          str
    :param log_level:           The level of log we want
    :type log_level:            int
    :param log_output:          Where do we should output the logs. Should be "stdout", "stderr", "syslog" or a file
    :type log_output:           str
    """
    task_lib = models.jobs.list_tasks()
    for task in task_lib:
        try:
            run_task(api_name, server_name, task['task'], task['job_id'], log_level, log_output)
        except StandardError as e:
            error_util.log_error(log, e)


def restart_server():
    """ Restart this python script """
    log.info("Restarting api server")
    time.sleep(1)
    os.execv(__file__, sys.argv)


def run_server(api_name, server_name, redis_host="localhost", redis_port=6379, data_db=0, pubsub_db=1,
               auto_reload=False, log_level=logging.INFO, log_output="syslog", pid_file=None):
    """
    Main loop function.
    It listen to pending jobs and run them.
    It will burn the recurring prices for files saved of storages.
    It also run a garbage collector to ensure killed jobs or faulty workers are cleaned.

    :param api_name:            The name of current API
    :type api_name:             str
    :param server_name:         The fqdn of current server
    :type server_name:          str
    :param data_db:             The redis database for data. Optional, default 0
    :type data_db:              int
    :param pubsub_db:           The redis database for pubsub events. Optional, default 1
    :type pubsub_db:            int
    :param redis_host:          The redis server to connect to. Optional, default "localhost"
    :type redis_host:           str
    :param redis_port:          The redis server port. Optional, default 6379
    :type redis_port:           int
    :param auto_reload:         Do we want the server to restart if the source code changed? Optional, default False
    :type auto_reload:          bool
    :param log_level:           The level of log we want
    :type log_level:            int
    :param log_output:          Where do we should output the logs. Should be "stdout", "stderr", "syslog" or a file
    :type log_output:           str
    :param pid_file:            The pid file to create if any, None otherwise
    :type pid_file:             str|None
    """
    # Write the pid file
    if pid_file:
        pid_file = os.path.join("/var", "run", api_name, api_name + ".pid")
        with open(pid_file, "w") as fh:
            fh.write(str(os.getpid()) + "\n")

    log.info("Starting " + api_name + " server")

    core.api_util.DatabaseContext.load_conf()
    core.api_util.RedisContext.set_params(api_name, server_name, redis_host, redis_port, data_db, pubsub_db)

    core.api_util.wait_for_postgres()
    queue = async_util.create_thread_queue()
    running_threads = []

    redis_thread = RedisReceiver(queue, api_name, server_name)
    running_threads.append(redis_thread)
    redis_thread.start()

    def reload_signal_handler(*args):
        queue.put({'type': SRC_CHANGED_MESSAGE, "data": None})

    signal.signal(signal.SIGUSR1, reload_signal_handler)

    burner_thread = PriceBurner()
    running_threads.append(burner_thread)
    burner_thread.start()

    price_updater_thread = PriceUpdater()
    running_threads.append(price_updater_thread)
    price_updater_thread.start()

    for provider in core.api_util.get_all_providers():
        if provider.type == "aws_spot":
            spot_thread = SpotIndexUpdater(provider)
            running_threads.append(spot_thread)
            spot_thread.start()

    if auto_reload:
        change_thread = SourceChangeNotifier(queue)
        running_threads.append(change_thread)
        change_thread.start()
        debug_util.register_for_debug()
    else:
        def ignore_signal(*args):
            log.info("Server not in debug mode, ignoring signal...")
        signal.signal(signal.SIGUSR2, ignore_signal)

    if GC_ENABLED:
        cmd = ["python", os.path.join(API_PATH, "app", "garbage_collector.py"),
               "--log-level", logging.getLevelName(log_level),
               "--log-output", log_output]
        if auto_reload:
            cmd.append("--debug")
        gc = subprocess.Popen(cmd)
    else:
        gc = None

    # Run all pending jobs we may have missed with a redis shutdown or a server.py shutdown
    run_pending_jobs(api_name, server_name, log_level, log_output)

    should_restart = False
    abort_exception = None

    while True:
        try:
            # Wait for events
            try:
                event = queue.get(block=True, timeout=60)
            except async_util.QueueEmpty:
                # No events during 1min, perhaps redis is dead so we check pending tasks
                run_pending_jobs(api_name, server_name, log_level, log_output)
                continue
            # Running
            msg_type = event['type']
            msg_data = event['data']
            if msg_type == REDIS_MESSAGE:
                run_task(api_name, server_name, msg_data['task'], msg_data['jobid'], log_level, log_output)
            elif msg_type == SRC_CHANGED_MESSAGE:
                should_restart = True
                break
            else:
                log.error("Unknown message received: "+str(msg_type))
        except error_util.abort_errors as e:
            abort_exception = e
            break
        except StandardError as e:
            error_util.log_error(log, e)

    try:
        log.info("Exit confirmed, cleaning...")
        for thread in running_threads:
            thread.stop()
        if gc:
            proc_util.ensure_stop_proc(gc)
        for thread in running_threads:
            thread.join()
    finally:
        if pid_file:
            try:
                os.remove(pid_file)
            except StandardError:
                pass
        log.info("Everything is cleaned")

    if abort_exception:
        raise abort_exception
    elif should_restart:
        restart_server()


def main():
    """
    Parse command arguments, initialize log and start launch `run_server`

    :return:        0 in case of success, between 1 and 127 in case of failure
    :rtype:         int
    """

    # Initialise and parse command arguments
    parser = argparse.ArgumentParser(description="Api service")
    parser.add_argument('--redis-host', '-H', help="Redis-server host")
    parser.add_argument('--redis-port', '-P', help='Redis-server connection port')
    parser.add_argument('--redis-data-db', '-i', help="Redis-server database index for data")
    parser.add_argument('--redis-pubsub-db', '-j', help="Redis-server database index for events")
    parser.add_argument('--log-level', '-l', help="log level (ex: info)")
    parser.add_argument('--log-output', help="log out, file path, 'syslog', 'stderr' or 'stdout'")
    parser.add_argument('--reload', '-r', action='store_true', help="Auto restart execution on code change")
    parser.add_argument('--pid-file', '-p', help="Pid file to set")

    args = parser.parse_args()

    # Load config
    conf = core.api_util.get_conf()
    api_name = conf.get('general', 'api_name')
    server_name = conf.get('general', "server")

    # Initialise logging
    if args.log_level:
        log_level = args.log_level.strip().upper()
    elif conf.has_section("log") and conf.has_option("log", "server_level"):
        log_level = conf.get("log", "server_level").strip().upper()
    else:
        log_level = "WARNING"
    log_level_int = logging.getLevelName(log_level)
    if not type_util.is_int(log_level_int):
        sys.stderr.write("Error: Invalid logging level "+repr(log_level)+"\n")
        sys.stderr.flush()
        return 1
    logging.getLogger().setLevel(logging.INFO if log_level_int < logging.INFO else log_level_int)
    log.setLevel(log_level_int)

    if args.log_output:
        log_output = args.log_output.strip().lower()
    elif conf.has_section("log") and conf.has_option("log", "server_output"):
        log_output = conf.get("log", "server_output").strip().lower()
    else:
        log_output = "stderr"
    if log_output in ("stderr", "stdout"):
        log_file = sys.stderr if log_output == "stderr" else sys.stdout
        if log_file.isatty():
            use_color = not util.env_is_off("LOG_COLOR")
        else:
            use_color = util.env_is_on("LOG_COLOR")
        if use_color:
            log_format = "%(log_color)s%(levelname)-8s%(blue)s%(name)-16s%(reset)s %(white)s%(message)s"
            log_handler = colorlog.StreamHandler(stream=log_file)
            log_handler.setFormatter(colorlog.ColoredFormatter(log_format))
        else:
            log_handler = logging.StreamHandler(stream=log_file)
            log_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    elif log_output == "syslog":
        log_handler = logging.handlers.SysLogHandler(address='/dev/log')
        log_handler.setFormatter(logging.Formatter('%(levelname)s %(module)s P%(process)d T%(thread)d %(message)s'))
    else:
        log_handler = logging.FileHandler(log_output)
        log_handler.setFormatter(logging.Formatter('%(asctime)s: %(levelname)-7s: %(name)s - %(message)s'))
    logging.getLogger().addHandler(log_handler)
    log.addHandler(log_handler)
    log.propagate = False

    # Get Redis config
    if args.redis_host:
        redis_host = args.redis_host.strip()
    elif conf.has_section("redis") and conf.has_option("redis", "host"):
        redis_host = conf.get("redis", "host").strip()
    else:
        redis_host = "localhost"
    if args.redis_port:
        redis_port = int(args.redis_port.strip())
    elif conf.has_section("redis") and conf.has_option("redis", "port"):
        redis_port = int(conf.get("redis", "port").strip())
    else:
        redis_port = 6379
    if args.redis_data_db:
        redis_data_db = int(args.redis_data_db.strip())
    elif conf.has_section("redis") and conf.has_option("redis", "data_db"):
        redis_data_db = int(conf.get("redis", "data_db").strip())
    else:
        redis_data_db = 0
    if args.redis_pubsub_db:
        redis_pubsub_db = int(args.redis_pubsub_db.strip())
    elif conf.has_section("redis") and conf.has_option("redis", "pubsub_db"):
        redis_pubsub_db = int(conf.get("redis", "pubsub_db").strip())
    else:
        redis_pubsub_db = 1

    if args.reload:
        auto_reload = True
    elif util.env_is_on("AUTO_RELOAD_CODE"):
        auto_reload = True
    else:
        auto_reload = False

    # Launch the main function
    try:
        run_server(api_name, server_name,
                   redis_host, redis_port, redis_data_db, redis_pubsub_db,
                   auto_reload=auto_reload, log_level=log_level_int, log_output=log_output, pid_file=args.pid_file)
    except error_util.abort_errors:
        logging.getLogger("aziugo").info("Signal received, exiting")
        return 0
    except error_util.all_errors as e:
        logging.getLogger("aziugo").exception(str(e))
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
