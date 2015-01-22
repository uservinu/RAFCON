
from utils import log
logger = log.get_logger(__name__)

import gtk
from gtkmvc import Controller
from gtkmvc.adapters import UserClassAdapter
from mvc.controllers.transition_list import TransitionListController
from mvc.controllers.data_flow_list import DataFlowListController


class StateConnectionsEditorController(Controller):
    """Controller handling the view of properties/attributes of the ContainerStateModel and StateModel

    This :class:`gtkmvc.Controller` class is the interface between the GTK widget view
    :class:`mvc.views.state_properties.ContainerStateView` and the properties of the
    :class:`mvc.models.state.ContainerStateModel`. Changes made in
    the GUI are written back to the model and vice versa.

    :param mvc.models.StateModel model: The state model containing the data
    :param mvc.views.StatePropertiesView view: The GTK view showing the data as a table
    """

    def __init__(self, model, view):
        """Constructor
        """
        Controller.__init__(self, model, view)
        self.transitions_ctrl = TransitionListController(model, view.transitions_view)
        self.dataflows_ctrl = DataFlowListController(model, view.dataflows_view)
        self.view_dict = {'transitions_internal': True, 'transitions_external': True,
                          'dataflows_internal': True, 'dataflows_external': True}

    def register_view(self, view):
        """Called when the View was registered

        Can be used e.g. to connect signals. Here, the destroy signal is connected to close the application
        """
        view['add_t_button'].connect('clicked', self.on_add_transition_clicked)
        view['cancel_t_edit_button'].connect('clicked', self.on_cancel_transition_edit_clicked)
        view['remove_t_button'].connect('clicked', self.on_remove_transition_clicked)
        view['connected_to_t_checkbutton'].connect('toggled', self.toggled_button, 'transitions_external')
        view['internal_t_checkbutton'].connect('toggled', self.toggled_button, 'transitions_internal')

        view['add_d_button'].connect('clicked', self.on_add_transition_clicked)
        view['cancel_d_edit_button'].connect('clicked', self.on_cancel_dataflow_edit_clicked)
        view['remove_d_button'].connect('clicked', self.on_remove_dataflow_clicked)
        view['connected_to_d_checkbutton'].connect('toggled', self.toggled_button, 'dataflows_external')
        view['internal_d_checkbutton'].connect('toggled', self.toggled_button, 'dataflows_internal')

        # view['state_properties_view'].set_model(self.model.list_store)
        #
        # view['value_renderer'].connect('edited', self.__property_edited)

    def register_adapters(self):
        """Adapters should be registered in this method call

        Each property of the state should have its own adapter, connecting a label in the View with the attribute of
        the State.
        """
        #self.adapt(self.__state_property_adapter("name", "input_name"))

    # def __property_edited(self, _, row, value):
    #     outcome = self.model.update_row(row, value)
    #     if type(outcome) != bool:
    #         logger.warning("Invalid value: %s" % outcome)
    #

    def on_add_transition_clicked(self, widget, data=None):
        print "add_t: %s" % widget

    def on_cancel_transition_edit_clicked(self, widget, data=None):
        print "cancel_t: %s" % widget

    def on_remove_transition_clicked(self, widget, data=None):
        print "rm_t: %s" % widget

    def on_add_dataflow_clicked(self, widget, data):
        print "add_d: %s" % widget

    def on_cancel_dataflow_edit_clicked(self, widget, data=None):
        print "cancel_d: %s" % widget

    def on_remove_dataflow_clicked(self, widget, data=None):
        print "rm_d: %s" % widget

    def toggled_button(self, button, name=None):
        self.view_dict[name] = button.get_active()
        print(name, "was turned", self.view_dict[name])  # , "\n", self.view_dict

    def __state_property_adapter(self, attr_name, label, view=None, value_error=None):
        """Helper method returning an adapter for a state property

        The method creates a custom adapter connecting a widget/label in the View with an attribute of the state model.

        :param attr_name: The name of the attribute
        :param label: The label of the widget element
        :param view: A reference to the view containing the widget. If left out, the view of the controller is used.
        :param val_error_fun: An optional function handling a value_error exception. By default a debug message is
            print out and the widget value is updated to the previous value.
        :return: The custom created adapter, which can be used in :func:`register_adapter`
        """
        # if view is None:
        #     view = self.view
        #
        # if value_error is None:
        #     value_error = self._value_error
        #
        # adapter = UserClassAdapter(self.model, "state",
        #                            getter=lambda state: state.__getattribute__(attr_name),
        #                            setter=lambda state, value: state.__setattr__(attr_name, value),
        #                            value_error=value_error)
        # adapter.connect_widget(view[label])
        # return adapter
    
    @staticmethod
    def _value_error(adapt, prop_name, value):
        logger.warning("Invalid value '{val:s}' for key '{prop:s}'.".format(val=value, prop=prop_name))
        adapt.update_widget()  # Update widget values with values from model

    # @Controller.observe("state", before=True)
    # def before_state_change(self, model, _, info):
    #     """Called before an attribute of the state is set
    #
    #     The attributes of the state should all be set via function (setters). An observer observes these functions
    #     and calls this function before the actual setter call. It passes several parameters for information purpose.
    #
    #     The function is empty at the moment (except a debug output), but can be filled with logic executed before a
    #     certain attribute is changed. The method contains a comment with example code.
    #
    #     :param mvc.models.StateModel model: The model of the state being handled by the controller
    #     :param sm.State _: The state that was changed (can also be accessed via the model)
    #     :param info: Additional information, such as the method name that was called to change an attribute. With
    #         this method name, the property being changed can be determined. The parameter also contains the new desired
    #         value.
    #
    #     """
    #
    #     logger.debug("before_state_change -- Attribute: %s, before: %s, desired: %s",
    #                  info.method_name, model.state.__getattribute__(info.method_name), info.args[1])
    #
    #     # The name of the method called th change the attribute should coincide with the attribute's name
    #     # attr = info.method_name
    #     #
    #     # if attr == "id"
    #     #     # The ID of the state is being changed
    #     #     pass
    #     # elif attr == "name"
    #     #     # The name of the state is being changed
    #     #     pass
    #
    #     pass
    #
    #
    # @Controller.observe("state", after=True)
    # def after_state_change(self, model, _, info):
    #     """Called after an attribute of the state was set
    #
    #     The attributes of the state should all be set via function (setters). An observer observes these functions
    #     and calls this function after the actual setter call. It passes several parameters for information purpose.
    #
    #     The function is empty at the moment (except a debug output), but can be filled with logic executed before a
    #     certain attribute is changed. See :func:`before_state_change` for example code.
    #
    #     :param mvc.models.StateModel model: The model of the state being handled by the controller
    #     :param sm.State _: The state that was changed (can also be accessed via the model)
    #     :param info: Additional information, such as the method name that was called to change an attribute. With
    #         this method name, the property being changed can be determined. The parameter also contains the new desired
    #         value and the return value of the setter function. By comparing the passed attribute with the current
    #         one, it can be determined whether the value was successfully changed or not.
    #
    #     """
    #
    #     logger.debug("after_state_change -- Attribute: %s, after: %s, desired: %s, returned: %s",
    #                  info.method_name, model.state.__getattribute__(info.method_name), info.args[1], info.result)
    #
    #     if model.state.__getattribute__(info.method_name) == info.args[1]:  # Change was successful
    #
    #         if self.view is None:  # View hasn't been created, yet
    #             self.model.update_attributes()
    #
    #         # If the view has been created, store the current selection of the table and restore the selection,
    #         # after the table has been updated. This is needed, as the selection is lost when the table is cleared.
    #         else:
    #             view = self.view['state_properties_view']
    #
    #             selection = view.get_selection()
    #             (paths, _) = selection.get_selected_rows()
    #             selected_paths = []
    #             for path in paths:
    #                 if selection.path_is_selected(path.path):
    #                     selected_paths.append(path.path)
    #
    #             self.model.update_attributes()
    #
    #             for path in selected_paths:
    #                 selection.select_path(path)

if __name__ == '__main__':
    from mvc.controllers import SingleWidgetWindowController
    from mvc.views import StateConnectionsEditorView, SingleWidgetWindowView

    import mvc.main as main

    main.setup_path()
    main.check_requirements()
    [ctr_model, logger, ctr_state, gvm_model, emm_model] = main.create_models()

    v = SingleWidgetWindowView(StateConnectionsEditorView, width=500, height=200, title='Connection Editor')
    c = SingleWidgetWindowController(ctr_model, v, StateConnectionsEditorController)
    #c = SingleWidgetWindowController(ctr_model.states.values()[1], v, StateConnectionsEditorController)

    gtk.main()