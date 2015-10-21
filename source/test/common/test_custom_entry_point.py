# core elements
from rafcon.statemachine.execution.statemachine_execution_engine import StatemachineExecutionEngine
from rafcon.statemachine.states.execution_state import ExecutionState
from rafcon.statemachine.states.hierarchy_state import HierarchyState

# singleton elements
import rafcon.statemachine.singleton

# test environment elements
import test_utils
import pytest


def test_custom_entry_point(caplog):
    test_utils.remove_all_libraries()

    rafcon.statemachine.singleton.state_machine_manager.delete_all_state_machines()
    test_utils.test_multithrading_lock.acquire()

    start_state_id = "RWUZOP/ZDWBKU/HADSLI"
    sm = StatemachineExecutionEngine.execute_state_machine_from_path(
        rafcon.__path__[0] + "/../test_scripts/unit_test_state_machines/test_custom_entry_point", start_state_id)
    rafcon.statemachine.singleton.state_machine_manager.remove_state_machine(sm.state_machine_id)
    assert not rafcon.statemachine.singleton.global_variable_manager.variable_exist("start_id21")

    test_utils.assert_logger_warnings_and_errors(caplog)
    test_utils.test_multithrading_lock.release()


if __name__ == '__main__':
    pytest.main([__file__])