from gtkmvc import Model, Observable

from awesome_server.connections.udp_connection import UDPConnection


class UDPConnectionModel(Model, Observable):

    _udp_clients_list = []
    udp_connection = None

    __observables__ = ("_udp_clients_list", "udp_connection")

    def __init__(self, udp_connection):
        Model.__init__(self)
        Observable.__init__(self)
        self.register_observer(self)

        assert isinstance(udp_connection, UDPConnection)
        self.udp_connection = udp_connection

    @Model.observe("udp_connection", after=True)
    def model_changed(self, model, prop_name, info):
        if info["method_name"] == "append_client":
            self._udp_clients_list.append(info["args"][1])

    @property
    def udp_client_list(self):
        return self._udp_clients_list