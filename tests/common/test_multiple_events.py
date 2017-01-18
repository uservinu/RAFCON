import pytest
import threading
import time

# core elements
from rafcon.core.singleton import state_machine_manager
from rafcon.core.singleton import global_variable_manager
from rafcon.core.singleton import state_machine_execution_engine

# test environment elements
import testing_utils


def trigger_exectuion_engine(gvm, execution_engine):

    while not gvm.variable_exist("sm_status"):
        time.sleep(0.1)

    while gvm.get_variable("sm_status") != 0:
        time.sleep(0.1)

    execution_engine.pause()

    while gvm.get_variable("sm_status") != 1:
        time.sleep(0.1)

    execution_engine.start()
    while gvm.get_variable("sm_status") != 2:
        time.sleep(0.1)

    execution_engine.stop()


def test_multi_events(caplog):
    testing_utils.remove_all_libraries()

    state_machine_manager.delete_all_state_machines()
    testing_utils.test_multithreading_lock.acquire()

    execution_trigger_thread = threading.Thread(target=trigger_exectuion_engine,
                                                args=[global_variable_manager, state_machine_execution_engine])
    execution_trigger_thread.start()

    sm = state_machine_execution_engine.execute_state_machine_from_path(
        path=testing_utils.get_test_sm_path("unit_test_state_machines/multi_events_test"))

    execution_trigger_thread.join()
    state_machine_manager.remove_state_machine(sm.state_machine_id)
    assert global_variable_manager.get_variable("sm_status") == 2

    testing_utils.reload_config()
    testing_utils.assert_logger_warnings_and_errors(caplog, 0, 0)
    testing_utils.test_multithreading_lock.release()


if __name__ == '__main__':
    # test_multi_events(None)
    pytest.main([__file__])