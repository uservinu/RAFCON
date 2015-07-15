from weakref import ref

from gaphas.connector import PointPort, Handle

from awesome_tool.mvc.models.outcome import OutcomeModel
from awesome_tool.mvc.models.data_port import DataPortModel
from awesome_tool.mvc.models.scoped_variable import ScopedVariableModel

from awesome_tool.utils import constants

from awesome_tool.mvc.controllers.gap import gap_draw_helper

from gtkmvc.model import Model

from math import pi

import cairo
from pango import SCALE, FontDescription
from gtk.gdk import Color, CairoContext

from awesome_tool.mvc.controllers.gap.enums import SnappedSide, Direction


class PortView(Model, object):

    side = None

    __observables__ = ('side', )

    def __init__(self, in_port, port_side_size, name=None, parent=None, side=SnappedSide.RIGHT):
        Model.__init__(self)
        self.handle = Handle(connectable=True)
        self.port = PointPort(self.handle.pos)
        self._side = None
        self.side = side
        self._parent = parent

        self._fill = False
        self._draw_connection_to_port = True

        if self._fill:
            self.text_color = constants.STATE_BACKGROUND_COLOR
            self.fill_color = constants.LABEL_COLOR
        else:
            self.text_color = constants.LABEL_COLOR
            self.fill_color = constants.LABEL_COLOR

        self._incoming_handles = []
        self._outgoing_handles = []
        self._connected_connections = []
        self._tmp_incoming_connected = False
        self._tmp_outgoing_connected = False

        self._name = name

        self._is_in_port = in_port

        self._port_side_size = port_side_size
        self.update_port_side_size()

    @property
    def side(self):
        return self._side

    @side.setter
    @Model.setter('side')
    def side(self, side):
        assert isinstance(side, SnappedSide)
        self._side = side

    @property
    def port_side_size(self):
        return self._port_side_size

    @port_side_size.setter
    def port_side_size(self, port_side_size):
        self._port_side_size = port_side_size

    @property
    def name(self):
        return self._name

    @property
    def parent(self):
        return self._parent

    @property
    def pos(self):
        return self.handle.pos

    @property
    def handle_pos(self):
        return self.handle.pos

    @property
    def port_pos(self):
        return self.port.point

    def has_outgoing_connection(self):
        return len(self._outgoing_handles) > 0

    def has_incoming_connection(self):
        return len(self._incoming_handles) > 0

    def add_connected_handle(self, handle, connection_view, moving=False):
        from awesome_tool.mvc.views.gap.connection import ConnectionView
        assert isinstance(handle, Handle)
        assert isinstance(connection_view, ConnectionView)
        if not moving and handle is connection_view.from_handle() and handle not in self._outgoing_handles:
            self._outgoing_handles.append(handle)
            self._add_connection(connection_view)
        elif not moving and handle is connection_view.to_handle() and handle not in self._incoming_handles:
            self._incoming_handles.append(handle)
            self._add_connection(connection_view)

    def _add_connection(self, connection_view):
        if connection_view not in self._connected_connections:
            self._connected_connections.append(connection_view)

    def remove_connected_handle(self, handle):
        assert isinstance(handle, Handle)
        if handle in self._incoming_handles:
            self._incoming_handles.remove(handle)
            for conn in self._connected_connections:
                if conn.to_handle() is handle:
                    self._connected_connections.remove(conn)
        elif handle in self._outgoing_handles:
            self._outgoing_handles.remove(handle)
            for conn in self._connected_connections:
                if conn.from_handle() is handle:
                    self._connected_connections.remove(conn)

    def tmp_connect(self, handle, connection_view):
        if handle is connection_view.from_handle():
            self._tmp_outgoing_connected = True
        elif handle is connection_view.to_handle():
            self._tmp_incoming_connected = True

    def tmp_disconnect(self):
        self._tmp_incoming_connected = False
        self._tmp_outgoing_connected = False

    @property
    def connected_outgoing(self):
        if len(self._outgoing_handles) == 0:
            return self._tmp_outgoing_connected
        return True

    @property
    def connected_incoming(self):
        if len(self._incoming_handles) == 0:
            return self._tmp_incoming_connected
        return True

    def is_connected_to_scoped_variable(self):
        from awesome_tool.mvc.views.gap.connection import ScopedVariableDataFlowView
        for conn in self._connected_connections:
            if isinstance(conn, ScopedVariableDataFlowView):
                return True
        return False

    def draw(self, context, state):
        raise NotImplementedError

    def draw_port(self, context, fill_color):
        self.update_port_side_size()
        c = context.cairo
        outcome_side = self.port_side_size
        c.set_line_width(outcome_side * 0.03)

        direction = None

        if self.side is SnappedSide.LEFT:
            direction = Direction.RIGHT if self._is_in_port else Direction.LEFT
        elif self.side is SnappedSide.TOP:
            direction = Direction.DOWN if self._is_in_port else Direction.UP
        elif self.side is SnappedSide.RIGHT:
            direction = Direction.LEFT if self._is_in_port else Direction.RIGHT
        elif self.side is SnappedSide.BOTTOM:
            direction = Direction.UP if self._is_in_port else Direction.DOWN

        # Outer part
        self._draw_triangle(self.pos, direction, c, outcome_side, draw_inner=False)
        # c.rectangle(self.pos.x - outcome_side / 2, self.pos.y - outcome_side / 2, outcome_side, outcome_side)
        c.move_to(0, 0)
        c.set_source_color(Color('#000'))
        c.fill_preserve()
        c.set_source_color(Color(fill_color))
        c.stroke()

        # Inner part
        if self.connected_incoming and self.connected_outgoing:
            self._draw_triangle(self.pos, direction, c, outcome_side, draw_inner=True)
        elif self.connected_incoming:
            self._draw_triangle_half(self.pos, direction, c, outcome_side, front_part=False)
        elif self.connected_outgoing:
            self._draw_triangle_half(self.pos, direction, c, outcome_side, front_part=True)
        c.set_source_color(Color(fill_color))
        c.fill_preserve()
        c.set_source_rgba(0, 0, 0, 0)
        c.stroke()

        if self.name and not self.has_outgoing_connection():  # and self.parent.parent:
            self.draw_name(context)

    def draw_name(self, context):
        if self.is_connected_to_scoped_variable():
            return

        outcome_side = self.port_side_size
        c = context.cairo

        # Ensure that we have CairoContext anf not CairoBoundingBoxContext (needed for pango)
        if isinstance(c, CairoContext):
            cc = c
        else:
            cc = c._cairo

        pcc = CairoContext(cc)
        pcc.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

        layout = pcc.create_layout()
        layout.set_text(self.name)

        font_name = constants.FONT_NAMES[0]
        font_size = outcome_side

        font = FontDescription(font_name + " " + str(font_size))
        layout.set_font_description(font)

        text_size = (layout.get_size()[0] / float(SCALE), layout.get_size()[1] / float(SCALE))

        print_side = self.side if not self.parent.selected else self.side.opposite()

        rot_angle, move_x, move_y = gap_draw_helper.draw_name_label(context, self.fill_color, text_size, self.pos,
                                                                    print_side, self.port_side_size,
                                                                    self._draw_connection_to_port, self._fill)

        c.move_to(move_x, move_y)

        cc.set_source_color(Color(self.text_color))

        pcc.update_layout(layout)
        pcc.rotate(rot_angle)
        pcc.show_layout(layout)
        pcc.rotate(-rot_angle)

        c.move_to(outcome_side, outcome_side)

    @staticmethod
    def _draw_triangle(pos, direction, context_cairo, outcome_side, draw_inner):
        c = context_cairo

        side_half = outcome_side / 2.

        if draw_inner:
            multiplier = .8
            multiplier_comp_1 = multiplier * 1.125
            multiplier_comp_2 = multiplier * 1.05
        else:
            multiplier = 1.
            multiplier_comp_1 = 1.
            multiplier_comp_2 = 1.

        if direction is Direction.UP:
            c.move_to(pos.x, pos.y - side_half * multiplier)
            c.line_to(pos.x - side_half * multiplier_comp_2, pos.y + side_half * multiplier_comp_1)
            c.line_to(pos.x + side_half * multiplier_comp_2, pos.y + side_half * multiplier_comp_1)
            c.line_to(pos.x, pos.y - side_half * multiplier)
        elif direction is Direction.DOWN:
            c.move_to(pos.x, pos.y + side_half * multiplier)
            c.line_to(pos.x - side_half * multiplier_comp_2, pos.y - side_half * multiplier_comp_1)
            c.line_to(pos.x + side_half * multiplier_comp_2, pos.y - side_half * multiplier_comp_1)
            c.line_to(pos.x, pos.y + side_half * multiplier)
        elif direction is Direction.LEFT:
            c.move_to(pos.x - side_half * multiplier, pos.y)
            c.line_to(pos.x + side_half * multiplier_comp_1, pos.y - side_half * multiplier_comp_2)
            c.line_to(pos.x + side_half * multiplier_comp_1, pos.y + side_half * multiplier_comp_2)
            c.line_to(pos.x - side_half * multiplier, pos.y)
        elif direction is Direction.RIGHT:
            c.move_to(pos.x + side_half * multiplier, pos.y)
            c.line_to(pos.x - side_half * multiplier_comp_1, pos.y - side_half * multiplier_comp_2)
            c.line_to(pos.x - side_half * multiplier_comp_1, pos.y + side_half * multiplier_comp_2)
            c.line_to(pos.x + side_half * multiplier, pos.y)

    @staticmethod
    def _draw_triangle_half(pos, direction, context_cairo, outcome_side, front_part):
        c = context_cairo

        multiplier_comp_1 = 1.125
        multiplier_comp_2 = 1.05

        side_half = outcome_side / 2. * .8
        side_quarter = outcome_side / 4. * .8

        if direction is Direction.UP:
            if front_part:
                c.move_to(pos.x - side_quarter, pos.y)
                c.line_to(pos.x, pos.y - side_half)
                c.line_to(pos.x + side_quarter, pos.y)
                c.line_to(pos.x - side_quarter, pos.y)
            else:
                c.move_to(pos.x - side_quarter, pos.y)
                c.line_to(pos.x + side_quarter, pos.y)
                c.line_to(pos.x + side_half * multiplier_comp_2, pos.y + side_half * multiplier_comp_1)
                c.line_to(pos.x - side_half * multiplier_comp_2, pos.y + side_half * multiplier_comp_1)
                c.line_to(pos.x - side_quarter, pos.y)
        elif direction is Direction.DOWN:
            if front_part:
                c.move_to(pos.x - side_quarter, pos.y)
                c.line_to(pos.x, pos.y + side_half)
                c.line_to(pos.x + side_quarter, pos.y)
                c.line_to(pos.x - side_quarter, pos.y)
            else:
                c.move_to(pos.x - side_quarter, pos.y)
                c.line_to(pos.x + side_quarter, pos.y)
                c.line_to(pos.x + side_half * multiplier_comp_2, pos.y - side_half * multiplier_comp_1)
                c.line_to(pos.x - side_half * multiplier_comp_2, pos.y - side_half * multiplier_comp_1)
                c.line_to(pos.x - side_quarter, pos.y)
        elif direction is Direction.LEFT:
            if front_part:
                c.move_to(pos.x, pos.y - side_quarter)
                c.line_to(pos.x - side_half, pos.y)
                c.line_to(pos.x, pos.y + side_quarter)
                c.line_to(pos.x, pos.y - side_quarter)
            else:
                c.move_to(pos.x, pos.y - side_quarter)
                c.line_to(pos.x, pos.y + side_quarter)
                c.line_to(pos.x + side_half * multiplier_comp_1, pos.y + side_half * multiplier_comp_2)
                c.line_to(pos.x + side_half * multiplier_comp_1, pos.y - side_half * multiplier_comp_2)
                c.line_to(pos.x, pos.y - side_quarter)
        elif direction is Direction.RIGHT:
            if front_part:
                c.move_to(pos.x, pos.y - side_quarter)
                c.line_to(pos.x + side_half, pos.y)
                c.line_to(pos.x, pos.y + side_quarter)
                c.line_to(pos.x, pos.y - side_quarter)
            else:
                c.move_to(pos.x, pos.y - side_quarter)
                c.line_to(pos.x, pos.y + side_quarter)
                c.line_to(pos.x - side_half * multiplier_comp_1, pos.y + side_half * multiplier_comp_2)
                c.line_to(pos.x - side_half * multiplier_comp_1, pos.y - side_half * multiplier_comp_2)
                c.line_to(pos.x, pos.y - side_quarter)

    def update_port_side_size(self):
        return
        # if self._parent:
        #     self._port_side_size = min(self._parent.width, self._parent.height) / 20.
        # else:
        #     self._port_side_size = 5.


class IncomeView(PortView):

    def __init__(self, parent, port_side_size):
        super(IncomeView, self).__init__(in_port=True, port_side_size=port_side_size, parent=parent, side=SnappedSide.LEFT)

    def draw(self, context, state):
        self.draw_port(context, "#fff")


class OutcomeView(PortView):

    def __init__(self, outcome_m, parent, port_side_size):
        super(OutcomeView, self).__init__(in_port=False, port_side_size=port_side_size, name=outcome_m.outcome.name, parent=parent)

        assert isinstance(outcome_m, OutcomeModel)
        self._outcome_m = ref(outcome_m)
        self.sort = outcome_m.outcome.outcome_id

    @property
    def outcome_m(self):
        return self._outcome_m()

    @property
    def outcome_id(self):
        return self.outcome_m.outcome.outcome_id

    @property
    def name(self):
        return self.outcome_m.outcome.name

    def draw(self, context, state):
        if self.outcome_id == -2:
            fill_color = '#00f'
        elif self.outcome_id == -1:
            fill_color = '#f00'
        else:
            fill_color = '#fff'

        self.draw_port(context, fill_color)


class ScopedVariablePortView(PortView):

    def __init__(self, parent, port_side_size, scoped_variable_m):
        super(ScopedVariablePortView, self).__init__(False, port_side_size, parent=parent, side=SnappedSide.TOP)

        assert isinstance(scoped_variable_m, ScopedVariableModel)
        self._scoped_variable_m = ref(scoped_variable_m)

    @property
    def model(self):
        return self._scoped_variable_m()

    @property
    def port_id(self):
        return self.model.scoped_variable.data_port_id

    @property
    def name(self):
        return self.model.scoped_variable.name

    def draw(self, context, state):
        name_size = self._get_name_size(context)

        self.update_port_side_size()
        c = context.cairo
        outcome_side = self.port_side_size

        self._draw_rectangle(c, name_size[0], outcome_side)
        c.set_source_color(Color('#ffbf00'))
        c.fill_preserve()
        c.stroke()

        self.draw_name(context)

    def draw_name(self, context):
        outcome_side = self.port_side_size
        c = context.cairo

        # Ensure that we have CairoContext anf not CairoBoundingBoxContext (needed for pango)
        if isinstance(c, CairoContext):
            cc = c
        else:
            cc = c._cairo

        pcc = CairoContext(cc)
        pcc.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

        layout = pcc.create_layout()
        layout.set_text(self.name)

        font_name = constants.FONT_NAMES[0]
        font_size = outcome_side * .8

        font = FontDescription(font_name + " " + str(font_size))
        layout.set_font_description(font)

        name_size = layout.get_size()[0] / float(SCALE), layout.get_size()[1] / float(SCALE)

        cc.set_source_color(Color('#ededee'))

        rot_angle = .0
        draw_pos = self._get_draw_position(name_size[0], outcome_side)

        if self.side is SnappedSide.RIGHT:
            c.move_to(draw_pos[0] + outcome_side, draw_pos[1])
            rot_angle = pi / 2
        elif self.side is SnappedSide.LEFT:
            c.move_to(draw_pos[0], draw_pos[1] + name_size[0])
            rot_angle = - pi / 2
        elif self.side is SnappedSide.TOP or self.side is SnappedSide.BOTTOM:
            c.move_to(draw_pos[0], draw_pos[1])

        pcc.update_layout(layout)
        pcc.rotate(rot_angle)
        pcc.show_layout(layout)
        pcc.rotate(-rot_angle)

        c.move_to(*self.pos)

    def _draw_rectangle(self, context_cairo, text_width, port_height):
        c = context_cairo

        text_width_half = text_width / 2. + port_height * .2

        draw_pos = self._get_draw_position(text_width, port_height)

        if self.side is SnappedSide.TOP or self.side is SnappedSide.BOTTOM:
            c.rectangle(draw_pos[0], draw_pos[1], text_width_half * 2., port_height)
        elif self.side is SnappedSide.LEFT or self.side is SnappedSide.RIGHT:
            c.rectangle(draw_pos[0], draw_pos[1], port_height, text_width_half * 2.)

    def _get_draw_position(self, text_width, port_height):
        text_width_half = text_width / 2. + port_height * .2
        height_half = port_height / 2.

        offset = .0

        if self.side is SnappedSide.TOP or self.side is SnappedSide.BOTTOM:
            if self.pos.x - text_width_half < 0:
                offset = self.pos.x - text_width_half
            elif self.pos.x + text_width_half > self.parent.width:
                offset = self.pos.x + text_width_half - self.parent.width
            return self.pos.x - text_width_half - offset, self.pos.y - height_half
        elif self.side is SnappedSide.LEFT or self.side is SnappedSide.RIGHT:
            if self.pos.y - text_width_half < 0:
                offset = self.pos.y - text_width_half
            elif self.pos.y + text_width_half > self.parent.height:
                offset = self.pos.y + text_width_half - self.parent.height
            return self.pos.x - height_half, self.pos.y - text_width_half - offset

    def _get_name_size(self, context):
        outcome_side = self.port_side_size
        c = context.cairo

        # Ensure that we have CairoContext anf not CairoBoundingBoxContext (needed for pango)
        if isinstance(c, CairoContext):
            cc = c
        else:
            cc = c._cairo

        pcc = CairoContext(cc)
        pcc.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

        layout = pcc.create_layout()
        layout.set_text(self.name)

        font_name = constants.FONT_NAMES[0]
        font_size = outcome_side * .8

        font = FontDescription(font_name + " " + str(font_size))
        layout.set_font_description(font)

        return layout.get_size()[0] / float(SCALE), layout.get_size()[1] / float(SCALE)


class ScopedDataPortView(PortView):

    def __init__(self, in_port, parent, scoped_variable_m, side):

        super(ScopedDataPortView, self).__init__(in_port=in_port, port_side_size=0, parent=parent, side=side)

        assert isinstance(scoped_variable_m, ScopedVariableModel)
        self._scoped_variable_m = ref(scoped_variable_m)

        self.update_port_side_size()

    @property
    def scoped_variable_m(self):
        return self._scoped_variable_m()

    @property
    def port_id(self):
        return self.scoped_variable_m.scoped_variable.data_port_id

    def draw(self, context, state):
        self.draw_port(context, '#ffc926')

    def update_port_side_size(self):
        if self._parent:
            self._port_side_size = min(self._parent.width, self._parent.height) / 5.
        else:
            self._port_side_size = 5.


class ScopedDataInputPortView(ScopedDataPortView):

    def __init__(self, parent, scoped_variable_m):
        super(ScopedDataInputPortView, self).__init__(True, parent, scoped_variable_m, SnappedSide.LEFT)


class ScopedDataOutputPortView(ScopedDataPortView):

    def __init__(self, parent, scoped_variable_m):
        super(ScopedDataOutputPortView, self).__init__(False, parent, scoped_variable_m, SnappedSide.RIGHT)


class DataPortView(PortView):

    def __init__(self, in_port, parent, port_m, side, port_side_size):
        assert isinstance(port_m, DataPortModel)
        super(DataPortView, self).__init__(in_port=in_port, port_side_size=port_side_size, name=port_m.data_port.name, parent=parent, side=side)

        self._port_m = ref(port_m)
        self.sort = port_m.data_port.data_port_id

        if self._fill:
            self.text_color = constants.STATE_BACKGROUND_COLOR
            self.fill_color = constants.DATA_PORT_COLOR
        else:
            self.text_color = constants.DATA_PORT_COLOR
            self.fill_color = constants.DATA_PORT_COLOR

    @property
    def port_m(self):
        return self._port_m()

    @property
    def port_id(self):
        return self.port_m.data_port.data_port_id

    @property
    def name(self):
        return self.port_m.data_port.name

    def draw(self, context, state):
        self.draw_port(context, constants.DATA_PORT_COLOR)


class InputPortView(DataPortView):

    def __init__(self, parent, port_m, port_side_size):
        super(InputPortView, self).__init__(True, parent, port_m, SnappedSide.LEFT, port_side_size)


class OutputPortView(DataPortView):

    def __init__(self, parent, port_m, port_side_size):
        super(OutputPortView, self).__init__(False, parent, port_m, SnappedSide.RIGHT, port_side_size)