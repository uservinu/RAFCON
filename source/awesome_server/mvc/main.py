from twisted.internet import gtk2reactor
gtk2reactor.install()

from twisted.internet import reactor

from awesome_server.mvc.views.debug_view import DebugView
from awesome_server.mvc.controller.debug_view import DebugViewController

from awesome_server.connections.connection_manager import ConnectionManager
from awesome_server.mvc.models.connection_manager import ConnectionManagerModel

import gtk


if __name__ == '__main__':

    debug_view = DebugView()

    connection_manager = ConnectionManager()
    connection_manager_model = ConnectionManagerModel(connection_manager)

    debug_view_ctrl = DebugViewController(connection_manager_model, debug_view)

    reactor.run()
    gtk.main()