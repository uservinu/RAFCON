import pytest
import rafcon
import test_utils

import rafcon.statemachine.states.execution_state
import rafcon.statemachine.states.hierarchy_state
import rafcon.statemachine.states.preemptive_concurrency_state

from rafcon.statemachine.singleton import global_variable_manager as gvm
from rafcon.statemachine.singleton import global_storage, state_machine_manager, state_machine_execution_engine


def assert_gvm(key, value=True):
    assert gvm.get_variable(key) == value


def assert_all_false(*elements):
    for elem in elements:
        assert not elem


class TestErrorPreemptionHandling():

    state_machine = None

    @classmethod
    def setup_class(cls):
        # This methods runs on class creation and creates the state machine
        test_utils.test_multithrading_lock.acquire()
        state_machine, version, creation_time = global_storage.load_statemachine_from_yaml(rafcon.__path__[0] +
                                                                                           "/../test_scripts/action_block_execution_test")
        cls.state_machine = state_machine
        state_machine_manager.add_state_machine(state_machine)
        state_machine_manager.active_state_machine_id = state_machine.state_machine_id

    @classmethod
    def teardown_class(cls):
        test_utils.test_multithrading_lock.release()
        pass

    def setup(self):
        # This methods runs before each test method and resets the global variables
        gvm.set_variable("wait_inner_observer_1", .2)
        gvm.set_variable("wait_inner_observer_2", .2)
        gvm.set_variable("wait_observer_1", .2)
        gvm.set_variable("wait_observer_2", .2)

        gvm.set_variable("inner_error_handler", False)
        gvm.set_variable("inner_exit_handler", False)
        gvm.set_variable("error_handler", False)
        gvm.set_variable("error_handler_2", False)
        gvm.set_variable("exit_handler", False)
        gvm.set_variable("exit_handler_2", False)

        gvm.set_variable("inner_observer_1_abort", False)
        gvm.set_variable("inner_observer_1_exception", False)
        gvm.set_variable("observer_1_abort", False)
        gvm.set_variable("observer_1_exception", False)

        gvm.set_variable("observer_1_finish", False)
        gvm.set_variable("observer_2_finish", False)
        gvm.set_variable("inner_observer_1_finish", False)
        gvm.set_variable("inner_observer_2_finish", False)

    def teardown(self):
        # variables_for_pytest.test_multithrading_lock.release()
        pass

    def run_state_machine(self):
        state_machine_execution_engine.start()
        self.state_machine.root_state.join()
        state_machine_execution_engine.stop()

    @staticmethod
    def assert_no_errors():
        # No error handler was executed occurred
        assert_gvm("error_handler", False)
        assert_gvm("error_handler_2", False)
        assert_gvm("inner_error_handler", False)

    def test_default_run(self, caplog):
        self.run_state_machine()
        self.assert_no_errors()
        test_utils.assert_logger_warnings_and_errors(caplog)

    def test_inner_observer_1_finish(self, caplog):
        gvm.set_variable("wait_inner_observer_1", .1)
        self.run_state_machine()
        self.assert_no_errors()
        assert_gvm("inner_observer_1_finish")
        assert_gvm("inner_exit_handler")
        assert_gvm("exit_handler")
        assert_gvm("exit_handler_2", False)
        assert_all_false(gvm.get_variable("inner_observer_2_finish"), gvm.get_variable("observer_1_finish"),
                         gvm.get_variable("observer_2_finish"))
        test_utils.assert_logger_warnings_and_errors(caplog)

    def test_inner_observer_2_finish(self, caplog):
        gvm.set_variable("wait_inner_observer_2", .1)
        self.run_state_machine()
        self.assert_no_errors()
        assert_gvm("inner_observer_2_finish")
        assert_gvm("inner_exit_handler")
        assert_gvm("exit_handler")
        assert_gvm("exit_handler_2", False)
        assert_all_false(gvm.get_variable("inner_observer_1_finish"), gvm.get_variable("observer_1_finish"),
                         gvm.get_variable("observer_2_finish"))
        test_utils.assert_logger_warnings_and_errors(caplog)

    def test_observer_1_finish(self, caplog):
        gvm.set_variable("wait_observer_1", .1)
        self.run_state_machine()
        self.assert_no_errors()
        assert_gvm("observer_1_finish")
        assert_gvm("inner_exit_handler")
        assert_gvm("exit_handler")
        assert_gvm("exit_handler_2")
        assert_all_false(gvm.get_variable("inner_observer_2_finish"), gvm.get_variable("inner_observer_1_finish"),
                         gvm.get_variable("observer_2_finish"))
        test_utils.assert_logger_warnings_and_errors(caplog)

    def test_observer_2_finish(self, caplog):
        gvm.set_variable("wait_observer_2", .1)
        self.run_state_machine()
        self.assert_no_errors()
        assert_gvm("observer_2_finish")
        assert_gvm("inner_exit_handler")
        assert_gvm("exit_handler")
        assert_gvm("exit_handler_2")
        assert_all_false(gvm.get_variable("inner_observer_2_finish"), gvm.get_variable("inner_observer_1_finish"),
                         gvm.get_variable("observer_1_finish"))
        test_utils.assert_logger_warnings_and_errors(caplog)

    def test_inner_observer_1_error(self, caplog):
        gvm.set_variable("wait_inner_observer_1", .1)
        gvm.set_variable("inner_observer_1_abort", True)
        self.run_state_machine()
        assert_gvm("inner_error_handler", False)
        assert_gvm("error_handler")
        assert_gvm("error_handler_2")
        assert_all_false(gvm.get_variable("inner_observer_1_finish"), gvm.get_variable("observer_1_finish"),
                         gvm.get_variable("observer_1_finish"), gvm.get_variable("observer_2_finish"))
        test_utils.assert_logger_warnings_and_errors(caplog)

    def test_inner_observer_1_exception(self, caplog):
        gvm.set_variable("wait_inner_observer_1", .1)
        gvm.set_variable("inner_observer_1_exception", True)
        self.run_state_machine()
        assert_gvm("inner_error_handler", False)
        assert_gvm("error_handler")
        assert_all_false(gvm.get_variable("inner_observer_1_finish"), gvm.get_variable("observer_1_finish"),
                         gvm.get_variable("observer_1_finish"), gvm.get_variable("observer_2_finish"))
        test_utils.assert_logger_warnings_and_errors(caplog, 0, 1)

    def test_observer_1_error(self, caplog):
        gvm.set_variable("wait_observer_1", .1)
        gvm.set_variable("observer_1_abort", True)
        self.run_state_machine()
        self.assert_no_errors()
        assert_all_false(gvm.get_variable("inner_observer_1_finish"), gvm.get_variable("observer_1_finish"),
                         gvm.get_variable("observer_1_finish"), gvm.get_variable("observer_2_finish"))
        test_utils.assert_logger_warnings_and_errors(caplog)

    def test_observer_1_exception(self, caplog):
        gvm.set_variable("wait_observer_1", .1)
        gvm.set_variable("observer_1_exception", True)
        self.run_state_machine()
        self.assert_no_errors()
        assert_all_false(gvm.get_variable("inner_observer_1_finish"), gvm.get_variable("observer_1_finish"),
                         gvm.get_variable("observer_1_finish"), gvm.get_variable("observer_2_finish"))
        test_utils.assert_logger_warnings_and_errors(caplog, 0, 1)

if __name__ == '__main__':
    pytest.main([__file__])