"""
Tools for Energy Model Optimization and Analysis (Temoa):
An open source framework for energy systems optimization modeling

Copyright (C) 2015,  NC State University

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

A complete copy of the GNU General Public License v2 (GPLv2) is available
in LICENSE.txt.  Users uncompressing this from an archive may not have
received this license file.  If not, see <http://www.gnu.org/licenses/>.


Written by:  J. F. Hyink
jeff@westernspark.us
https://westernspark.us
Created on:  11/9/24

A sequencer for Monte Carlo Runs
.
"""
import logging
import queue
import sqlite3
import time
import tomllib
from datetime import datetime
from logging import getLogger
from multiprocessing import Queue
from pathlib import Path

from definitions import PROJECT_ROOT, get_OUTPUT_PATH
from temoa.extensions.modeling_to_generate_alternatives.worker import Worker
from temoa.extensions.monte_carlo.mc_run import MCRunFactory
from temoa.temoa_model.hybrid_loader import HybridLoader
from temoa.temoa_model.table_writer import TableWriter
from temoa.temoa_model.temoa_config import TemoaConfig
from temoa.temoa_model.temoa_model import TemoaModel

logger = getLogger(__name__)

solver_options_path = Path(PROJECT_ROOT, 'temoa/extensions/monte_carlo/MC_solver_options.toml')


class MCSequencer:
    """
    A sequencer to control the steps in Monte Carlo run sequence
    """

    def __init__(self, config: TemoaConfig):
        self.config = config

        # read in the options
        try:
            with open(solver_options_path, 'rb') as f:
                all_options = tomllib.load(f)
            s_options = all_options.get(self.config.solver_name, {})
            logger.info('Using solver options: %s', s_options)

        except FileNotFoundError:
            logger.warning('Unable to find solver options toml file.  Using default options.')
            s_options = {}
            all_options = {}

        # worker options pulled from file
        self.num_workers = all_options.get('num_workers', 1)
        self.worker_solver_options = s_options

        # internal records
        self.solve_count = 0
        self.seen_instance_indices = set()
        self.orig_label = self.config.scenario

        self.writer = TableWriter(self.config)
        self.verbose = False  # for troubleshooting

    def start(self):
        """Run the sequencer"""
        # ==== basic sequence ====
        # 1. Load the model data, which may involve filtering it down if source tracing
        # 2. run a quick screen on the inputs using the data above as part of the screen
        #    before starting the long run
        # 3. make a queue for runs
        # 4. copy & modify the base data to make per-dataset runs
        # 5. farm out the runs to workers

        start_time = datetime.now()

        # 0. Set up database for scenario
        self.writer.clear_scenario()
        self.writer.make_mc_tweaks_table()  # add the output table for tweaks, if not exists
        self.writer.make_summary_flow_table()  # add the summary flow table, if not exists

        # 1. Load data
        with sqlite3.connect(self.config.input_database) as con:
            hybrid_loader = HybridLoader(db_connection=con, config=self.config)
        data_store = hybrid_loader.create_data_dict(myopic_index=None)
        mc_run = MCRunFactory(config=self.config, data_store=data_store)

        # 2. Screen the input file
        mc_run.prescreen_input_file()

        # 3. set up the run generator
        run_gen = mc_run.run_generator()

        # 4. Set up the workers
        num_workers = self.num_workers
        work_queue = Queue(1)  # restrict the queue to hold just 1 models in it max
        result_queue = Queue(
            num_workers + 1
        )  # must be able to hold a shutdown signal from all workers at once!
        log_queue = Queue(50)
        # make workers
        workers = []
        kwargs = {
            'solver_name': self.config.solver_name,
            'solver_options': self.worker_solver_options,
        }
        # construct path for the solver logs
        s_path = Path(get_OUTPUT_PATH(), 'solver_logs')
        if not s_path.exists():
            s_path.mkdir()
        for i in range(num_workers):
            w = Worker(
                model_queue=work_queue,
                results_queue=result_queue,
                log_root_name=__name__,
                log_queue=log_queue,
                log_level=logging.INFO,
                solver_log_path=s_path,
                **kwargs,
            )
            w.start()
            workers.append(w)
        # workers now running and waiting for jobs...

        # 6.  Start the iterative solve process and let the manager run the show
        more_runs = True
        # pull the first instance
        mc_run = next(run_gen)
        # capture the "tweaks"
        self.writer.write_tweaks(iteration=mc_run.run_index, change_records=mc_run.change_records)
        instance = mc_run.model
        while more_runs:
            try:
                work_queue.put(instance, block=False)  # put a log on the fire, if room
                logger.info('Putting an instance in the work queue')
                try:
                    mc_run = next(run_gen)
                    # capture the "tweaks"
                    self.writer.write_tweaks(
                        iteration=mc_run.run_index, change_records=mc_run.change_records
                    )
                    instance = mc_run.model
                except StopIteration:
                    logger.debug('Pulled last run from run generator')
                    more_runs = False
            except queue.Full:
                # print('work queue is full')
                pass
            # see if there is a result ready to pick up, if not, pass
            try:
                next_result = result_queue.get_nowait()
            except queue.Empty:
                next_result = None
                # print('no result')
            if next_result is not None:
                self.process_solve_results(next_result)
                logger.info('Solve count: %d', self.solve_count)
                self.solve_count += 1
                if self.verbose or not self.config.silent:
                    print(f'MC Solve count: {self.solve_count}')
            # pull anything from the logging queue and log it...
            while True:
                try:
                    record = log_queue.get_nowait()
                    process_logger = getLogger(record.name)
                    process_logger.handle(record)
                except queue.Empty:
                    break
            time.sleep(0.1)  # prevent hyperactivity...

        # 7. Shut down the workers and then the logging queue
        if self.verbose:
            print('shutting it down')
        for _ in workers:
            if self.verbose:
                print('shutdown sent')
            work_queue.put('ZEBRA')  # shutdown signal

        # 7b.  Keep pulling results from the queue to empty it out
        empty = 0
        while True:
            try:
                next_result = result_queue.get_nowait()
                if next_result == 'COYOTE':  # shutdown signal
                    empty += 1
            except queue.Empty:
                next_result = None
            if next_result is not None and next_result != 'COYOTE':
                logger.debug('bagged a result post-shutdown')
                self.process_solve_results(next_result)
                logger.info('Solve count: %d', self.solve_count)
                self.solve_count += 1
                if self.verbose or not self.config.silent:
                    print(f'MC Solve count: {self.solve_count}')
            while True:
                try:
                    record = log_queue.get_nowait()
                    process_logger = getLogger(record.name)
                    process_logger.handle(record)
                except queue.Empty:
                    break
            if empty == num_workers:
                break

        for w in workers:
            w.join()
            logger.debug('worker wrapped up...')

        log_queue.close()
        log_queue.join_thread()
        if self.verbose:
            print('log queue closed')
        work_queue.close()
        work_queue.join_thread()
        if self.verbose:
            print('work queue joined')
        result_queue.close()
        result_queue.join_thread()
        if self.verbose:
            print('result queue joined')

    def process_solve_results(self, instance: TemoaModel):
        """write the results as required"""
        # get the instance number from the model name, if provided
        if '-' not in instance.name:
            raise ValueError(
                'Instance name does not appear to contain a -idx value.  The manager should be tagging/updating this'
            )
        idx = int(instance.name.split('-')[-1])
        if idx in self.seen_instance_indices:
            raise ValueError(f'Instance index {idx} already seen.  Likely coding error')
        self.seen_instance_indices.add(idx)
        self.writer.write_mc_results(M=instance, iteration=idx)
