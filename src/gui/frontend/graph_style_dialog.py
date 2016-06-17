# -*- coding: utf-8 -*-

#
# graph_style_dialog.py
#
##############################################################################
#
# Copyright (c) 2015 Jorge Casas <jorcasas@ucm.es>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#
##############################################################################

import wx
import matplotlib
import platform
import numpy

from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigCanvas

def GetColorString(color):
	if platform.system() == "Darwin":
		return color
	else:
		return color.GetAsString(flags=wx.C2S_HTML_SYNTAX)

class GraphStyleDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.list_modes = wx.ListBox(self, -1, choices=[])
        self.sizer_list_modes_staticbox = wx.StaticBox(self, -1, _("List of graph style modes"))
        self.sizer_preview_staticbox = wx.StaticBox(self, -1, _("Preview"))
        self.label_bg_color = wx.StaticText(self, -1, _("Background color") + ": ")
        self.button_bg_color = wx.ColourPickerCtrl(self, -1, '#FFFFFF')
        self.label_grid_color = wx.StaticText(self, -1, _("Grid color") + ": ")
        self.button_grid_color = wx.ColourPickerCtrl(self, -1, '#666666')
        self.label_line_color = wx.StaticText(self, -1, _("Line color") + ": ")
        self.button_line_color = wx.ColourPickerCtrl(self, -1, '#0000FF')
        self.label_line_style = wx.StaticText(self, -1, _("Line style") + ": ")
        self.combo_line_style = wx.ComboBox(self, -1, choices=[_("Solid"), _("Dashed"), _("Dashdot"), _("Dotted")], style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.label_line_width = wx.StaticText(self, -1, _("Line width") + ": ")
        self.spin_line_width = wx.SpinCtrl(self, -1, "", min=1, max=10)
        self.sizer_customize_staticbox = wx.StaticBox(self, -1, _("Customize"))
	self.button_apply_style = wx.Button(self, -1, _("Apply graph style"))
        self.first_time = True
        self.is_customized = False

	self.dpi = 70
        self.fig = Figure((3.0, 3.0), dpi=self.dpi)
        self.fig.subplots_adjust(left=0.05, right=0.945, top=0.95, bottom=0.06) # Adjust the chart to occupy as much space the canvas
        self.axes = self.fig.add_subplot(111)
        self.plot_data = self.axes.plot([])[0]
        example_data_x = numpy.linspace(0, 10)
        example_data_y = numpy.power(2, example_data_x) / 10
	self.plot_data.set_xdata(example_data_x)
	self.plot_data.set_ydata(example_data_y)
	self.axes.set_xbound(lower=5, upper=10)
	self.axes.set_ybound(lower=1, upper=90)
        
        self.canvas = FigCanvas(self, -1, self.fig)

	self.__insert_style_modes()
        self.__set_properties()
        self.__do_layout()

	self.Bind(wx.EVT_LISTBOX, self.on_select_mode, self.list_modes)
	self.Bind(wx.EVT_LISTBOX_DCLICK, self.on_dclick_list_modes, self.list_modes)
	self.Bind(wx.EVT_COLOURPICKER_CHANGED, self.on_change_bg_color, self.button_bg_color)
	self.Bind(wx.EVT_COLOURPICKER_CHANGED, self.on_change_grid_color, self.button_grid_color)
	self.Bind(wx.EVT_COLOURPICKER_CHANGED, self.on_change_line_color, self.button_line_color)
	self.Bind(wx.EVT_COMBOBOX, self.on_change_line_style, self.combo_line_style)
	self.Bind(wx.EVT_SPINCTRL, self.on_change_line_width, self.spin_line_width)
	self.Bind(wx.EVT_BUTTON, self.on_apply_style, self.button_apply_style)

    def __set_properties(self):
        self.SetTitle(_("Graph style configuration"))
        self.SetSize((700, 530))
	self.list_modes.SetSelection(0)
        self.combo_line_style.SetSelection(0)
	self.button_apply_style.SetMinSize((230, 37))
	self.__set_colors('#FFFFFF', '#666666', '#0000FF', 0, 1)

    def __do_layout(self):
	separator = wx.BoxSizer(wx.VERTICAL)
        sizer_div = wx.BoxSizer(wx.HORIZONTAL)
        sizer_subdiv = wx.BoxSizer(wx.VERTICAL)
        self.sizer_customize_staticbox.Lower()
        sizer_customize = wx.StaticBoxSizer(self.sizer_customize_staticbox, wx.HORIZONTAL)
        grid_sizer_customize = wx.FlexGridSizer(5, 2, 5, 0)
        self.sizer_preview_staticbox.Lower()
        sizer_preview = wx.StaticBoxSizer(self.sizer_preview_staticbox, wx.HORIZONTAL)
        self.sizer_list_modes_staticbox.Lower()
        sizer_list_modes = wx.StaticBoxSizer(self.sizer_list_modes_staticbox, wx.HORIZONTAL)
        sizer_list_modes.Add(self.list_modes, 1, wx.ALL | wx.EXPAND, 5)
        sizer_div.Add(sizer_list_modes, 3, wx.ALL | wx.EXPAND, 5)
	sizer_preview.Add(self.canvas, 1, wx.EXPAND, 0)
        sizer_subdiv.Add(sizer_preview, 1, wx.ALL | wx.EXPAND, 5)
        grid_sizer_customize.Add(self.label_bg_color, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_sizer_customize.Add(self.button_bg_color, 0, wx.EXPAND, 0)
        grid_sizer_customize.Add(self.label_grid_color, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_sizer_customize.Add(self.button_grid_color, 0, wx.EXPAND, 0)
        grid_sizer_customize.Add(self.label_line_color, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_sizer_customize.Add(self.button_line_color, 0, wx.EXPAND, 0)
        grid_sizer_customize.Add(self.label_line_style, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_sizer_customize.Add(self.combo_line_style, 0, wx.EXPAND, 0)
        grid_sizer_customize.Add(self.label_line_width, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        grid_sizer_customize.Add(self.spin_line_width, 0, wx.EXPAND, 0)
        grid_sizer_customize.AddGrowableCol(1)
        sizer_customize.Add(grid_sizer_customize, 1, wx.ALL | wx.EXPAND, 5)
        sizer_subdiv.Add(sizer_customize, 0, wx.ALL | wx.EXPAND, 5)
        sizer_div.Add(sizer_subdiv, 4, wx.EXPAND, 0)
	separator.Add(sizer_div, 1, wx.EXPAND, 0)
	separator.Add(self.button_apply_style, 0, wx.RIGHT | wx.BOTTOM | wx.ALIGN_RIGHT, 5)
        self.SetSizer(separator)
        self.Layout()

    def __insert_style_modes(self):
        # Format for adding new graphics style modes:
	# self.list_modes.Append(<Mode name>, ModeStyle(<bg color>, <grid color>, <line color>, <num line style>, <num line width>))
	
	self.list_modes.Append(_("Default"), ModeStyle('#FFFFFF', '#666666', '#0000FF', 0, 1))
	self.list_modes.Append("Contrast", ModeStyle('#000000', '#FFFFFF', '#FFFFFF', 0, 1))
	self.list_modes.Append("Simple", ModeStyle('#FFFFFF', '#000000', '#000000', 0, 1))
	self.list_modes.Append("Hacker", ModeStyle('#000000', '#00FF00', '#00FF00', 0, 1))
	self.list_modes.Append("Aqua", ModeStyle('#0E2581', '#FFFFFF', '#00EDF6', 0, 1))
	self.list_modes.Append("Inferno", ModeStyle('#6B0000', '#FFFFFF', '#FF0000', 0, 1))
	self.list_modes.Append("Tropical", ModeStyle('#00B829', '#006207', '#FFFF00', 1, 2))
	self.list_modes.Append("Desert", ModeStyle('#A94000', '#FFC800', '#FFB612', 0, 1))
	self.list_modes.Append("Night", ModeStyle('#000000', '#FFFF00', '#FFFF00', 3, 2))

    def __get_name_line_style(self, n):
	name = None
	if n == 0: name = "solid"
	elif n == 1: name = "dashed"
	elif n == 2: name = "dashdot"
	elif n == 3: name = "dotted"
	return name

    def __set_colors(self, bg_color, grid_color, line_color, line_style, line_width):
	self.button_bg_color.SetColour(bg_color)
	self.button_grid_color.SetColour(grid_color)
	self.button_line_color.SetColour(line_color)
	self.combo_line_style.SetSelection(line_style)
	self.spin_line_width.SetValue(line_width)

	self.axes.set_axis_bgcolor(bg_color)
	self.axes.grid(True, color=grid_color)
	self.plot_data.set_color(line_color)
	self.plot_data.set_linestyle(self.__get_name_line_style(line_style))
	self.plot_data.set_linewidth(line_width)

	self.canvas.draw()

    def on_dclick_list_modes(self, event):
	style_conf = self.list_modes.GetClientData(self.list_modes.GetSelection())
	self.__set_colors(style_conf.bg_color, style_conf.grid_color, style_conf.line_color, style_conf.line_style, style_conf.line_width)
        self.EndModal(0)

    def on_select_mode(self, event):
        if self.first_time and self.is_customized:
	    self.list_modes.SetSelection(wx.NOT_FOUND)
            self.first_time = False
        else:
	    style_conf = self.list_modes.GetClientData(self.list_modes.GetSelection())
	    self.__set_colors(style_conf.bg_color, style_conf.grid_color, style_conf.line_color, style_conf.line_style, style_conf.line_width)
	
    def on_change_bg_color(self, event):
	new_bg_color = GetColorString(self.button_bg_color.GetColour()) 
	self.axes.set_axis_bgcolor(new_bg_color)
	self.canvas.draw()
	self.list_modes.SetSelection(wx.NOT_FOUND)

    def on_change_grid_color(self, event):
	new_grid_color = GetColorString(self.button_grid_color.GetColour()) 
	self.axes.grid(True, color=new_grid_color)
	self.canvas.draw()
	self.list_modes.SetSelection(wx.NOT_FOUND)

    def on_change_line_color(self, event):
	new_line_color = GetColorString(self.button_line_color.GetColour()) 
	self.plot_data.set_color(new_line_color)
	self.canvas.draw()
	self.list_modes.SetSelection(wx.NOT_FOUND)

    def on_change_line_style(self, event):
	new_line_style = self.combo_line_style.GetSelection()
	self.plot_data.set_linestyle(self.__get_name_line_style(new_line_style))
	self.canvas.draw()
	self.list_modes.SetSelection(wx.NOT_FOUND)

    def on_change_line_width(self, event):
	new_line_width = self.spin_line_width.GetValue()
	self.plot_data.set_linewidth(new_line_width)
	self.canvas.draw()
	self.list_modes.SetSelection(wx.NOT_FOUND)

    def on_apply_style(self, event):
	self.EndModal(0)

    def GetModeName(self):
	name_mode = None
	if self.list_modes.GetSelection() == wx.NOT_FOUND:
		name_mode = _("Customized")
        elif self.list_modes.GetSelection() == 0:
		name_mode = self.list_modes.GetString(self.list_modes.GetSelection())
        else:
		name_mode = _("{0} mode").format(self.list_modes.GetString(self.list_modes.GetSelection()))
	return name_mode

    def GetBgColor(self):
	return GetColorString(self.button_bg_color.GetColour()) 

    def GetGridColor(self):
	return GetColorString(self.button_grid_color.GetColour()) 

    def GetLineColor(self):
	return GetColorString(self.button_line_color.GetColour()) 

    def GetLineStyle(self):
	return self.__get_name_line_style(self.combo_line_style.GetSelection())

    def GetLineWidth(self):
	return self.spin_line_width.GetValue()

    def GetModeNumber(self):
        return self.list_modes.GetSelection()

    def GetLineStyleNumber(self):
        return self.combo_line_style.GetSelection()

    def SetModeNumber(self, nr_mode):
        self.list_modes.SetSelection(nr_mode)

	# It is neccesary to work on OSX systems
	style_conf = self.list_modes.GetClientData(nr_mode)
	self.__set_colors(style_conf.bg_color, style_conf.grid_color, style_conf.line_color, style_conf.line_style, style_conf.line_width)

    def SetCustomizedMode(self, bg_color, grid_color, line_color, line_style, line_width):
        self.is_customized = True
	self.__set_colors(bg_color, grid_color, line_color, line_style, line_width)
	self.list_modes.SetSelection(wx.NOT_FOUND)

class ModeStyle(object):

	def __init__(self, bg_color, grid_color, line_color, line_style, line_width):
		self.bg_color = bg_color
		self.grid_color = grid_color
		self.line_color = line_color
		self.line_style = line_style
		self.line_width = line_width
