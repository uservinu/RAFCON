#!/usr/bin/env python
# Copyright (C) 2015-2018 DLR
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Eclipse Public License v1.0 which
# accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v10.html
#
# Contributors:
# Annika Wollschlaeger <annika.wollschlaeger@dlr.de>
# Franz Steinmetz <franz.steinmetz@dlr.de>
# Lukas Becker <lukas.becker@dlr.de>
# Mahmoud Akl <mahmoud.akl@dlr.de>
# Matthias Buettner <matthias.buettner@dlr.de>
# Michael Vilzmann <michael.vilzmann@dlr.de>
# Rico Belder <rico.belder@dlr.de>
# Sebastian Brunner <sebastian.brunner@dlr.de>


# default libraries
import os
import sys
import logging
import gtk
import glib
import threading
import signal
from yaml_configuration.config import config_path

# gui
import rafcon
from rafcon.gui.config import global_gui_config
import rafcon.gui.singleton as gui_singletons
from rafcon.gui.controllers.main_window import MainWindowController
from rafcon.gui.views.main_window import MainWindowView
from rafcon.gui.runtime_config import global_runtime_config
import rafcon.gui.models.auto_backup
from rafcon.gui.utils.splash_screen import SplashScreen
from rafcon.gui.helpers import installation
import rafcon.gui.backup.session as backup_session

# state machine
from rafcon.core.start import parse_state_machine_path, setup_environment, reactor_required, \
    setup_configuration, post_setup_plugins, register_signal_handlers
from rafcon.core.state_machine import StateMachine
from rafcon.core.states.hierarchy_state import HierarchyState
import rafcon.core.singleton as core_singletons
from rafcon.core.execution.execution_status import StateMachineExecutionStatus
from rafcon.core.config import global_config

# utils
from rafcon.gui.utils import wait_for_gui
import rafcon.utils.filesystem as filesystem
from rafcon.utils import plugins
from rafcon.utils.i18n import _, setup_l10n, setup_l10n_gtk
from rafcon.utils import log

logger = log.get_logger("rafcon.start.gui")


def setup_installation():
    """Install necessary GUI resources
    
    By default, RAFCON should be installed via `setup.py` (`pip install rafcon`). Thereby, all resources are being 
    installed. However, if this is not the case, one can set the `RAFCON_CHECK_INSTALLATION` env variable to `True`. 
    Then, the installation will be performed before starting the GUI. 
    """
    if os.environ.get("RAFCON_CHECK_INSTALLATION", False) == "True":
        rafcon_root = os.path.dirname(rafcon.__file__)
        installation.assets_folder = os.path.join(rafcon_root, 'gui', 'assets')
        installation.share_folder = os.path.join(os.path.dirname(os.path.dirname(rafcon_root)), 'share')
        installation.install_fonts(logger, restart=True)
        installation.install_gtk_source_view_styles(logger)
        installation.install_libraries(logger, overwrite=False)


def setup_gtkmvc_logger():
    # Apply defaults to logger of gtkmvc
    for handler in logging.getLogger('gtkmvc').handlers:
        logging.getLogger('gtkmvc').removeHandler(handler)
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(logging.Formatter("%(asctime)s: %(levelname)-8s - %(name)s:  %(message)s"))
    stdout.setLevel(logging.DEBUG)
    logging.getLogger('gtkmvc').addHandler(stdout)


def install_reactor():
    from twisted.internet import gtk2reactor
    from twisted.internet.error import ReactorAlreadyInstalledError
    try:
        # needed for glib.idle_add, and signals
        gtk2reactor.install()
    except ReactorAlreadyInstalledError:
        pass


def pre_setup_plugins():
    """Loads plugins and calls the pre init hooks

    If twisted has been imported by a plugin, the gtk2reactor is installed
    """
    # load all plugins specified in the RAFCON_PLUGIN_PATH
    plugins.load_plugins()

    # check if twisted is imported and if so, install the required reactor
    if reactor_required():
        install_reactor()

    plugins.run_pre_inits()


def setup_mvc_environment():
    setup_environment()


def start_state_machine(state_machine, start_state_path, quit_flag):
    sm_thread = threading.Thread(target=start_stop_state_machine,
                                 args=[state_machine, start_state_path, quit_flag])
    sm_thread.start()


def start_stop_state_machine(state_machine, start_state_path, quit_flag):
    wait_for_gui()

    state_machine_execution_engine = core_singletons.state_machine_execution_engine
    state_machine_execution_engine.execute_state_machine_from_path(state_machine=state_machine,
                                                                   start_state_path=start_state_path,
                                                                   wait_for_execution_finished=True)
    if reactor_required():
        from twisted.internet import reactor
        reactor.callFromThread(reactor.stop)

    if quit_flag:
        gui_singletons.main_window_controller.get_controller('menu_bar_controller').on_quit_activate(None, None)


def setup_argument_parser():
    """Sets up teh parser with the required arguments

    :return: The parser object
    """
    default_config_path = filesystem.get_default_config_path()
    filesystem.create_path(default_config_path)

    parser = core_singletons.argument_parser
    parser.add_argument('-n', '--new', action='store_true', help=_("whether to create a new state-machine"))
    parser.add_argument('-o', '--open', action='store', nargs='*', type=parse_state_machine_path,
                        dest='state_machine_paths', metavar='path',
                        help=_("specify directories of state-machines that shall be opened. Paths must contain a "
                               "statemachine.json file"))
    parser.add_argument('-c', '--config', action='store', type=config_path, metavar='path', dest='config_path',
                        default=default_config_path, nargs='?', const=default_config_path,
                        help=_("path to the configuration file config.yaml. Use 'None' to prevent the generation of a "
                               "config file and use the default configuration. Default: {0}"
                               "").format(default_config_path))
    parser.add_argument('-g', '--gui_config', action='store', type=config_path, metavar='path', dest='gui_config_path',
                        default=default_config_path, nargs='?', const=default_config_path,
                        help=_("path to the configuration file gui_config.yaml. "
                               "Use 'None' to prevent the generation of a config file and use the default "
                               "configuration. Default: {0}").format(default_config_path))
    parser.add_argument('-ss', '--start_state_machine', dest='start_state_machine_flag', action='store_true',
                        help=_("a flag to specify if the first state machine of -o should be started after opening"))
    parser.add_argument('-s', '--start_state_path', metavar='path', dest='start_state_path', default=None, nargs='?',
                        help=_("path within a state machine to the state that should be launched which consists of "
                               "state ids e.g. QPOXGD/YVWJKZ where QPOXGD is the root state and YVWJKZ its child states"
                               " to start from."))
    parser.add_argument('-q', '--quit', dest='quit_flag', action='store_true',
                        help=_("a flag to specify if the gui should quit after launching a state machine"))
    return parser


def setup_mvc_configuration(core_config_path, gui_config_path, runtime_config_path):
    setup_configuration(core_config_path)
    gui_config_path, gui_config_file = filesystem.separate_folder_path_and_file_name(gui_config_path)
    global_gui_config.load(gui_config_file, gui_config_path)
    runtime_config_path, runtime_config_file = filesystem.separate_folder_path_and_file_name(runtime_config_path)
    global_runtime_config.load(runtime_config_file, runtime_config_path)


def setup_gui():
    # Create the GUI-View
    main_window_view = MainWindowView()

    # set the gravity of the main window controller to static to ignore window manager decorations and get
    # a correct position of the main window on the screen (else there are offsets for some window managers)
    main_window_view.get_top_widget().set_gravity(gtk.gdk.GRAVITY_STATIC)

    sm_manager_model = gui_singletons.state_machine_manager_model
    main_window_controller = MainWindowController(sm_manager_model, main_window_view)
    return main_window_controller


def start_gtk():
    # check if twisted is imported
    if reactor_required():
        from twisted.internet import reactor
        import threading
        is_main_thread = isinstance(threading.current_thread(), threading._MainThread)
        reactor.run(installSignalHandlers=is_main_thread)
    else:
        gtk.main()


def stop_gtk():
    # shutdown twisted correctly
    if reactor_required():
        from twisted.internet import reactor
        if reactor.running:
            reactor.callFromThread(reactor.stop)
        # Twisted can be imported without the reactor being used
        # => check if GTK main loop is running
        elif gtk.main_level() > 0:
            glib.idle_add(gtk.main_quit)
    else:
        glib.idle_add(gtk.main_quit)

    # Run the GTK loop until no more events are being generated and thus the GUI is fully destroyed
    wait_for_gui()


def post_gui_destruction():
    plugins.run_hook("post_destruction")

    if global_gui_config.get_config_value('AUTO_RECOVERY_LOCK_ENABLED'):
        rafcon.gui.models.auto_backup.remove_rafcon_instance_lock_file()


def open_state_machines(paths):
    import rafcon.gui.helpers.state_machine as gui_helper_state_machine
    first_sm = None
    for path in paths:
        try:
            sm = gui_helper_state_machine.open_state_machine(path=path, recent_opened_notification=True)
            if first_sm is None:
                first_sm = sm
        except Exception as e:
            logger.exception(_("Could not load state machine '{}': {}").format(path, e))
    return first_sm


def create_new_state_machine():
    root_state = HierarchyState()
    state_machine = StateMachine(root_state)
    core_singletons.state_machine_manager.add_state_machine(state_machine)


SIGNALS_TO_NAMES_DICT = dict((getattr(signal, n), n) for n in dir(signal) if n.startswith('SIG') and '_' not in n)


def signal_handler(signal, frame):
    state_machine_execution_engine = core_singletons.state_machine_execution_engine
    core_singletons.shut_down_signal = signal

    # in this case the print is on purpose the see more easily if the interrupt signal reached the thread
    print _("Signal '{}' received.\nExecution engine will be stopped and program will be shutdown!").format(
        SIGNALS_TO_NAMES_DICT.get(signal, "[unknown]"))

    try:
        if not state_machine_execution_engine.finished_or_stopped():
            state_machine_execution_engine.stop()
            state_machine_execution_engine.join(3)  # Wait max 3 sec for the execution to stop
    except Exception as e:
        import traceback
        print _("Could not stop state machine: {0} {1}").format(e.message, traceback.format_exc())

    try:
        gui_singletons.main_window_controller.prepare_destruction()
    except Exception as e:
        print "Exception while preparing destruction", e
        os._exit(1)

    stop_gtk()

    post_gui_destruction()

    # Do not use sys.exit() in signal handler:
    # http://thushw.blogspot.de/2010/12/python-dont-use-sysexit-inside-signal.html
    os._exit(0)


def main():

    # check if all env variables are set
    if not os.environ.get("HOME", False):
        logger.error("For starting RAFCON in GUI mode, the HOME environment variable has to be set!")
        return

    register_signal_handlers(signal_handler)

    splash_screen = SplashScreen(contains_image=True, width=530, height=350)
    splash_screen.rotate_image(random_=True)
    splash_screen.set_text(_("Starting RAFCON..."))
    while gtk.events_pending():
        gtk.main_iteration()

    setup_installation()
    setup_l10n()
    setup_l10n_gtk()

    splash_screen.set_text("Setting up logger...")
    setup_gtkmvc_logger()

    splash_screen.set_text("Initializing plugins...")
    pre_setup_plugins()

    splash_screen.set_text("Setting up environment...")
    setup_mvc_environment()

    parser = setup_argument_parser()
    user_input = parser.parse_args()

    splash_screen.set_text("Loading configurations...")
    setup_mvc_configuration(user_input.config_path, user_input.gui_config_path, user_input.gui_config_path)

    # create lock file -> keep behavior for hole instance
    if global_gui_config.get_config_value('AUTO_RECOVERY_LOCK_ENABLED'):
        rafcon.gui.models.auto_backup.generate_rafcon_instance_lock_file()

    # setup the gui before loading the state machine as then the debug console shows the errors that emerged during
    # loading the state state machine
    splash_screen.set_text("Loading GUI...")
    setup_gui()

    wait_for_gui()

    post_setup_plugins(user_input)

    state_machine = None
    if user_input.state_machine_paths:
        state_machine = open_state_machines(user_input.state_machine_paths)

    if user_input.new:
        create_new_state_machine()

    # initiate stored session # TODO think about a controller for this
    if not user_input.new and not user_input.state_machine_paths \
            and rafcon.gui.singleton.global_gui_config.get_config_value("SESSION_RESTORE_ENABLED"):
        glib.idle_add(backup_session.restore_session_from_runtime_config, priority=glib.PRIORITY_LOW)

    if state_machine and (user_input.start_state_machine_flag or state_machine.get_state_by_path(user_input.start_state_path)):
        start_state_machine(state_machine, user_input.start_state_path, user_input.quit_flag)

    splash_screen.destroy()
    try:
        start_gtk()

        logger.info(_("Main window was closed"))

    finally:
        post_gui_destruction()

    if core_singletons.state_machine_execution_engine.status.execution_mode == StateMachineExecutionStatus.STARTED:
        logger.info(_("Waiting for the state machine execution to finish"))
        core_singletons.state_machine_execution_engine.join()
        logger.info(_("State machine execution has finished"))

    logger.info(_("Exiting ..."))


if __name__ == '__main__':
    main()
