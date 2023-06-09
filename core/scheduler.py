# Copyright 2023, by Julien Cegarra & Benoît Valéry. All rights reserved.
# Institut National Universitaire Champollion (Albi, France).
# License : CeCILL, version 2.1 (see the LICENSE file)
import os
import threading
import time

import pygetwindow
import win32gui
from pywinauto import Desktop
from pyglet.app import EventLoop
from pythonosc import osc_server
from pythonosc.dispatcher import Dispatcher

from core.scenario import Event
from core.clock import Clock
from core.modaldialog import ModalDialog
from core.logger import logger

import pyglet.clock
import sys


class Scheduler:
    """
    This class manages events execution.
    """

    def __init__(self, events, plugins, win, clock_speed, display_session_number):
        self.events = events
        self.plugins = plugins
        self.display_session_number = display_session_number

        logger.log_manual_entry(open('VERSION', 'r').read().strip(), key='version')

        if 'scheduling' in self.plugins:
            self.plugins['scheduling'].set_planning(self.events)

        # Link performance plugin to other plugins
        if 'performance' in self.plugins:
            self.plugins['performance'].plugins = self.plugins

        # Attribute Window to plugins
        self.win = win
        for i, p in self.plugins.items():
            p.win = self.win

        self.clock = Clock(clock_speed, 'main')
        self.pause_scenario_time = False
        self.scenariotime = 0

        # Used in replay to stop simulate clock
        self.target_time = 0
        # We store events in a list in case their execution is delayed by a blocking event
        self.events_queue = list()
        self.blocking_plugin = None

        # Store the plugins that could be paused by a *blocking* event
        self.paused_plugins = list()

        # Display window and create the event loop
        self.win.set_visible(True)

        self.clock.schedule(self.update)
        self.event_loop = EventLoop()
        self.server = None

        self.condition = None
        self.workload = None
        self.count_time = 0


    def update(self, dt):
        if self.win.modal_dialog is not None:
            return

        # Display the session ID if need be
        if self.display_session_number:
            msg = _('Session ID: %s') % logger.session_id
            self.win.modal_dialog = ModalDialog(self.win, msg, title='Session ID')
            self.display_session_number = False

        # Update timers with dt
        if not self.is_scenario_time_paused():
            self.scenariotime += dt
            logger.set_scenariotime(self.scenariotime)

        # Detect a potential blocking plugin
        active_blocking_plugin = self.get_active_blocking_plugin()

        # Execute scenario events in case the scenario timer is running
        if not self.is_scenario_time_paused():
            if active_blocking_plugin is None:
                event = self.get_event_at_scenario_time(self.scenariotime)
                if event is not None:
                    self.execute_one_event(event)

            # Check if a blocking plugin has started so to pause concurrent plugins
            elif active_blocking_plugin.alive:
                # Toggle scenario_time pause only once
                if not self.is_scenario_time_paused():
                    self.pause_scenario_time = True
                    self.paused_plugins = self.get_active_non_blocking_plugins()
                    self.execute_plugins_methods(self.paused_plugins, methods=[['pause']])

        elif active_blocking_plugin is None:
            if len(self.paused_plugins) > 0:
                self.execute_plugins_methods(self.paused_plugins, methods=[['resume']])
                self.paused_plugins = list()
            self.pause_scenario_time = False

        # Check if there are active plugins...
        ap = self.get_active_plugins()

        # ... if so, update them
        if len(ap) > 0:
            [p.update(self.scenariotime) for p in ap]
        # ... if not, and no remaining events, close the OpenMATB
        elif len(self.events_queue) == 0:
            self.exit()

        # If the windows has been killed, exit the program
        if self.win.alive == False:
            self.exit()

        # else:
        #    self.move_scenario_time_to(0) # in replay restart

    def is_scenario_time_paused(self):
        return self.pause_scenario_time is True

    def get_active_blocking_plugin(self):
        p = self.get_plugins_by_states([('blocking', True), ('paused', False)])
        if len(p) > 0:
            return p[0]

    def get_active_non_blocking_plugins(self):
        return self.get_plugins_by_states([('blocking', False), ('paused', False)])

    def get_active_plugins(self):
        return self.get_plugins_by_states([('alive', True)])

    def execute_one_event(self, event):
        # IDEA : the event could be scheduled (immediately) by the plugin clock
        # (all the events should be processed the same way)

        # Set the plugin corresponding to the event
        plugin = self.plugins[event.plugin]

        # If one argument, assume it is a plugin method to execute
        if len(event.command) == 1:
            getattr(plugin, event.command[0])()

        # If two arguments in the 'command' field, suppose a (parameter, value) to update
        elif len(event.command) == 2:
            getattr(plugin, 'set_parameter')(event.command[0], event.command[1])

        event.done = 1

        if self.win.replay_mode:
            plugin.update(0)

        # The event can be logged whenever inside the method, since self.durations remain
        # constant all along it
        logger.record_event(event)

    def execute_plugins_methods(self, plugins, methods):
        if len(plugins) == 0:
            return

        if isinstance(methods, str):
            methods = [methods]

        for m in methods:
            for p in plugins:
                self.execute_one_event(Event(0, 0, p.alias, m))

    def get_plugins_by_states(self, attribute_state_list):
        plugins = {k: p for k, p in self.plugins.items()}
        for (attribute, state) in attribute_state_list:
            plugins = {k: p for k, p in plugins.items() if getattr(p, attribute) == state}
        return [p for _, p in plugins.items()]

    def get_event_at_scenario_time(self, scenario_time: float):
        if self.win.replay_mode and scenario_time > self.target_time:
            self.scenario_clock.pause('replay')
            return self.unqueue_event()

        # Retrieve (simultaneous) events matching scenario_duration_sec
        # We look to the most precise point in the near future that might matches a set of event time(s)
        events_time = [event for event in self.events
                       if event.time_sec <= scenario_time]

        # In replay filter events that are under the target time limit
        events_time = [event for event in events_time
                       if not self.win.replay_mode or event.time_sec <= self.target_time]

        # Filter events that are either done or already in the queue
        events_time = [event for event in events_time
                       if event.done != 1]

        # Sort them according to their line number (ascending order)
        # and append the listed events in the correct order
        for event in sorted(events_time, key=lambda x: x.line):
            if event not in self.events_queue:
                self.events_queue.append(event)

        return self.unqueue_event()

    def unqueue_event(self):
        # If some events must be executed, unstack the next event
        if len(self.events_queue) > 0:
            event = self.events_queue[0]
            del self.events_queue[0]
            return event

        return None

    def move_scenario_time_to(self, time: float):
        if time < self.scenario_clock.get_time():
            # moving backward, we need to reset plugins, done events and restart from zero
            for plugin in self.plugins:
                self.plugins[plugin].stop(0)

            for event in self.events:
                event.done = False

            self.initialize_plugins()

            self.scenario_clock.set_time(0)

        # moving forward
        replay_acceleration_factor = 100

        self.target_time = time
        self.scenario_clock.set_speed(10.1)
        self.scenario_clock.resume('replay')
        self.clock.set_speed(replay_acceleration_factor)

    def move_scenariotime(self, time):
        if time < self.scenariotime:
            for plugin in self.plugins:
                self.plugins[plugin].scenariotime = time
                self.target_time = time
                self.plugins[plugin].next_refresh_time = time
                # print(self.plugins[plugin].alias)
                # print(self.plugins[plugin].next_refresh_time)

            # for event in self.events:
            # event.done = False

        events_time = [event for event in self.events if event.done != 1]

        self.scenariotime = time

    def play_scenario(self, target_time):
        self.clock.set_speed(5)
        self.scenario_clock.set_speed(5)
        self.scenario_clock.resume('replay')
        self.target_time = target_time

    def stop_scenario(self):
        # TODO: check if remaining events
        self.scenario_clock.pause('replay')

    def exit(self):
        logger.log_manual_entry('end')
        self.event_loop.exit()
        self.stop_server()
        self.win.close()
        sys.exit(0)

    def run(self):
        self.event_loop.run()

    def start_server(self):
        print("Starting Server OpenMATB")
        matb_dispatcher = Dispatcher()
        matb_dispatcher.map("/conditionfinish", self.on_finish_message)
        matb_dispatcher.map("/workload", self.on_workload_message)
        matb_dispatcher.map("/next", self.block_rcvd)
        matb_dispatcher.map("/trial", self.trial_rcvd)
        matb_dispatcher.map("/stop", self.on_stop)
        self.server = osc_server.ThreadingOSCUDPServer(("127.0.0.3", 5005), matb_dispatcher)
        print("OpenMATB serving on {}".format(self.server.server_address))
        thread = threading.Thread(target=self.server.serve_forever)
        thread.start()

    def stop_server(self):
        print("Stopping Server OpenMATB")
        if self.server:
            self.server.shutdown()
            #self.server.server_close()
            self.server = None
            print("Server OpenMATB stopped")
        else:
            print("Server is not running")

    def on_finish_message(self, address, *args):
        if address == "/conditionfinish":
            finish = args[0]

            if finish and self.condition != "practice":
                self.count_time += 720
                self.scenariotime = self.count_time
                logger.log_manual_entry(f"end block workload {self.workload}% & condition {self.condition}", 'endBlock')

            if logger.title == 'generated/practice_tactilient.txt':
                self.count_time += 720
                self.scenariotime = self.count_time
                logger.log_manual_entry(f"end block workload {self.workload}% & condition {self.condition}", 'endBlock')

            if logger.title == 'generated/practice_tactilient-matb.txt':
                self.count_time += 720
                self.scenariotime = self.count_time
                logger.log_manual_entry(f"end block workload {self.workload}% & condition {self.condition}", 'endBlock')

    def on_workload_message(self, address, *args):
        if address == "/workload":
            self.workload = args[0]
            self.condition = args[1]

            if self.workload == 'None':
                self.workload = 0
            elif self.workload == 'Moderate':
                self.workload = 30
            else:
                self.workload = 70

            if self.condition != 'practice':
                time.sleep(1.7)
                logger.log_manual_entry(f"start block workload {self.workload}% & condition {self.condition}", 'startBlock')

    def block_rcvd(self, address, *args):
        if address == '/next':
            next_b = args[0]
            self.let_focus("main.py")

            if next_b:
                plugin = self.get_active_blocking_plugin()
                if plugin is not None:
                    plugin.do_next()

    def on_stop(self, address, *args):
        if address == "/stop":
            stop_expe = args[0]
            if stop_expe:
                self.exit()

    def trial_rcvd(self, address, *args):
        if address == "/trial":
            stimulus = args[0]
            time = args[1]
            if self.condition != 'practice':
                logger.log_manual_entry(f"Playing trial stimulus {stimulus}", 'stimulus', time)

    def let_focus(self, window_name):
        desktop = Desktop(backend="uia").window(title=window_name)
        if desktop.exists():
            desktop.set_focus()
        else:
            print(f"Aucune fenêtre avec le nom '{window_name}' n'a été trouvée.")
