import subprocess
import os
import gtk
import threading
import Queue

# mvc elements
import rafcon.mvc.singleton
import rafcon.mvc.config as gui_config
from rafcon.mvc.controllers.main_window import MainWindowController
from rafcon.mvc.views.main_window import MainWindowView

# core elements
import rafcon.statemachine.config
import rafcon.statemachine.singleton

# general tool elements
import rafcon.utils.filesystem as fs
import rafcon.utils.log as log

# test environment elements
import testing_utils as t_u

logger = log.get_logger(__name__)


def find_running_process(process_name):

    popen_return_string = str(os.popen("ps cax | grep " + process_name).read())

    if not popen_return_string:
        logger.debug("popen | grep <process_name> didn't returned None")
        return False
    running = popen_return_string.split(' ')

    for entry in running:
        if (process_name + '\n') in entry:
            return True
    return False


def kill_running_processes(process_name):
    popen_return_string = str(os.popen("ps cax | grep " + process_name).read())

    if not popen_return_string:
        return
    running = popen_return_string.split('\n')
    running.pop()
    for entry in running:
        parts = entry.split(' ')
        os.system('kill ' + parts[0])


def check_for_editor(editor):
    try:
        subprocess.Popen(editor)
        kill_running_processes(editor)
        return True
    except OSError:
        return False


def trigger_source_editor_signals(main_window_controller):

    # ---setup---
    menubar_ctrl = main_window_controller.get_controller('menu_bar_controller')

    # ---setup new statemachine and add a new state---
    t_u.call_gui_callback(menubar_ctrl.on_new_activate, None)
    t_u.call_gui_callback(menubar_ctrl.on_add_state_activate, None)

    # ---focus the newly added state and get the source controller---
    sm_m = menubar_ctrl.model.get_selected_state_machine_model()
    root_state_m = sm_m.root_state
    state_m = root_state_m.states.values()[0]
    states_editor_controller = main_window_controller.get_controller('states_editor_ctrl')
    state_identifier = states_editor_controller.get_state_identifier(state_m)
    t_u.call_gui_callback(states_editor_controller.activate_state_tab, state_m)
    tab_list = states_editor_controller.tabs
    source_editor_controller = tab_list[state_identifier]['controller'].get_controller('source_ctrl')

    # ---check if the default text equals the default_script.py
    default_content = fs.read_file(os.path.join(rafcon.__path__[0], 'statemachine', 'default_script.py'))
    content = source_editor_controller.source_text
    assert content == default_content

    # ---check if the source text can be changed---
    content = 'Test'
    t_u.call_gui_callback(source_editor_controller.set_script_text, content)
    assert content == source_editor_controller.source_text

    # ---check if a wrong shell command returns false by the append_...() method
    assert not t_u.call_gui_callback(source_editor_controller.append_shell_command_to_path, 'gibberish', 'foo.txt')

    source_view = source_editor_controller.view
    test_text = 'apply_test'

    # get the textview buffer and replace the buffer text with another
    test_buffer = source_view.get_buffer()
    test_buffer.set_text(test_text, 10)

    # ---check if a new buffer doesnt change the source text
    source_view.textview.set_buffer(test_buffer)
    assert not source_editor_controller.source_text == test_text

    # ---check if the cancel button resets the buffer to the source text
    cancel_button = source_view['cancel_button']
    t_u.call_gui_callback(source_editor_controller.cancel_clicked, cancel_button)
    assert source_view.get_buffer().get_text(test_buffer.get_start_iter(), test_buffer.get_end_iter()) == content

    # test buffer now contains the source_text which equals content so test_buffer is again set to contain test_text
    test_buffer.set_text(test_text, 10)

    # ---check if changing the buffer and applying the changes has an impact on the source text
    source_view.textview.set_buffer(test_buffer)
    print ("test_buffer " + test_buffer.get_text(test_buffer.get_start_iter(), test_buffer.get_end_iter()))
    apply_button = source_view['apply_button']
    t_u.call_gui_callback(source_editor_controller.apply_clicked, apply_button)
    assert source_editor_controller.source_text == test_text

    # ----------- Test requiring gedit to work ------------
    if not check_for_editor('gedit'):
        t_u.call_gui_callback(menubar_ctrl.prepare_destruction)
        return False

    # ---check if the open external button opens a gedit instance

    kill_running_processes('gedit')
    gui_config.global_gui_config.set_config_value('DEFAULT_EXTERNAL_EDITOR', 'gedit')
    button = source_view['open_external_button']

    t_u.call_gui_callback(button.set_active, True)
    assert find_running_process('gedit')
    assert button.get_label() == 'Unlock'

    kill_running_processes('gedit')

    t_u.call_gui_callback(button.set_active, False)
    assert button.get_label() == 'Open externally'

    t_u.call_gui_callback(menubar_ctrl.prepare_destruction)
    return True


def test_gui(caplog):
    t_u.start_rafcon()

    t_u.remove_all_libraries()
    gui_config.global_gui_config.set_config_value('GAPHAS_EDITOR', True)
    gui_config.global_gui_config.set_config_value('AUTO_BACKUP_ENABLED', False)
    gui_config.global_gui_config.set_config_value('CHECK_PYTHON_FILES_WITH_PYLINT', False)

    # Wait for GUI to initialize
    t_u.wait_for_gui()
    t_u.sm_manager_model = rafcon.mvc.singleton.state_machine_manager_model
    main_window_view = MainWindowView()
    main_window_controller = MainWindowController(t_u.sm_manager_model, main_window_view)

    queue = Queue.Queue()
    thread = threading.Thread(target=lambda q, arg1: q.put(trigger_source_editor_signals(arg1)), 
                              args=(queue, main_window_controller))
    thread.start()

    gtk.main()
    logger.debug("after gtk main")
    thread.join()
    result = queue.get()
    
    # The queue exists because I want to catch the return value of my test method. This enables printing the error about 
    # the nonexistence of my required editor while still being able to finish the test in a "passed" state
    
    errors = 1
    if not result:
        logger.error("!The editor required in this test was not found on this machine. Test was aborted!")
        errors = 2
        
    t_u.test_multithreading_lock.release()
    t_u.assert_logger_warnings_and_errors(caplog, expected_errors=errors)


if __name__ == '__main__':
    test_gui(None)