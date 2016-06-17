# -*- coding: utf-8 -*-

#
# user_config.py
# Objects to store the user graphical configuration.
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

import re
import parser

class HWEvent(object):
	
	def __init__(self, num_counter, fixed, code=None, flags={}):
		self.num_counter = num_counter
		self.fixed = fixed
		self.code = code
		self.flags = flags


class Metric(object):

	def __init__(self, name, str_metric):
		self.name = name
		self.str_metric = str_metric

                # Adapts the metric to be readable by the pmctrack command data extractor (pmc_extract.py)
		str_metric_mod = re.sub(r"pmc(\d+)", r"float(field[self.pos['pmc\1']])", str_metric)
		str_metric_mod = re.sub(r"virt(\d+)", r"float(field[self.pos['virt\1']])", str_metric_mod)

		self.metric = parser.expr(str_metric_mod).compile()


class Experiment(object):
	
	def __init__(self):
		self.metrics = []
		self.eventsHW = []
                self.ebs_counter = -1 # Indicates the counter is used as EBS (-1 means 'none')
                self.ebs_value = ""


class MachineConfig(object):
	
	def __init__(self, type_machine, remote_address=None, remote_port=22, remote_user=None, remote_password=None, path_key=None):
		self.type_machine = type_machine # "local", "ssh" or "adb"
		self.remote_address = remote_address
		self.remote_port = remote_port
		self.remote_user = remote_user
		self.remote_password = remote_password
		self.path_key = path_key

	def GetSSHCommand(self):
		ssh_command = "ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=no"
		if self.remote_password != "":
			ssh_command = "sshpass -p {0} ".format(self.remote_password) + ssh_command
		else:
			ssh_command += " -o NumberOfPasswordPrompts=0"
			if self.path_key != "":
				ssh_command += " -i " + self.path_key
		if self.remote_port != 22:
			ssh_command += " -p " + str(self.remote_port)
		ssh_command += " -l " + self.remote_user
		ssh_command += " " + self.remote_address
		return ssh_command

	def GetADBCommand(self):
		return "adb -H " + self.remote_address + " -P " + self.remote_port + " shell"

		
class GraphStyleConfig(object):

	def __init__(self, bg_color, grid_color, line_color, line_style, line_width, line_style_number, mode_number):
                self.bg_color = bg_color
                self.grid_color = grid_color
                self.line_color = line_color
                self.line_style = line_style
                self.line_width = line_width
                self.line_style_number = line_style_number
                self.mode_number = mode_number

class UserConfig(object):
	
	def __init__(self):
		self.experiments = [] # List of experiments
                self.virtual_counters = [] # List of selected virtual counters
		self.machine = None # Information about monitoring machine
		self.applications = []
		self.cpu = None # CPU number where to run benchmark, or CPU mask
		self.pmctrack_path = None # Path to pmctrack command
		self.time = 0 # Time between samples (in miliseconds)
                self.buffer_size = 0 # Samples buffer size (in bytes)
		self.pid_app_running = None # Application's PID (if app to monitor is running)
                self.system_wide = False # Indicates if system-wide mode is activated
                self.save_counters_log = False
                self.save_metrics_log = False
		self.path_outfile_logs = None
		self.graph_style = None # Information about graph style

	def GetCopy(self):
		copy = UserConfig()
		copy.machine = MachineConfig(self.machine.type_machine, self.machine.remote_address, self.machine.remote_port, self.machine.remote_user, self.machine.remote_password, self.machine.path_key)
		num_exp = 0

		for experiment in self.experiments:
			copy.experiments.append(Experiment())
			for metric in experiment.metrics:
				copy.experiments[num_exp].metrics.append(Metric(metric.name, metric.str_metric))
			for eventHW in experiment.eventsHW:
				flags_copy = {}
                                for key in eventHW.flags.keys():
                                    flags_copy[key] = eventHW.flags[key]
				copy.experiments[num_exp].eventsHW.append(HWEvent(eventHW.num_counter, eventHW.fixed, eventHW.code, flags_copy))
                        copy.experiments[num_exp].ebs_counter = experiment.ebs_counter
                        copy.experiments[num_exp].ebs_value = experiment.ebs_value
			num_exp += 1

                for vcounter in self.virtual_counters:
                    copy.virtual_counters.append(vcounter)

                for application in self.applications:
                    copy.applications.append(application)
		copy.cpu = self.cpu
		copy.pmctrack_path = self.pmctrack_path
		copy.time = self.time
		copy.buffer_size = self.buffer_size
		copy.pid_app_running = self.pid_app_running
                copy.system_wide = self.system_wide
                copy.save_counters_log = self.save_counters_log
                copy.save_metrics_log = self.save_metrics_log
		copy.path_outfile_logs = self.path_outfile_logs
		copy.graph_style = GraphStyleConfig(self.graph_style.bg_color, self.graph_style.grid_color, self.graph_style.line_color, self.graph_style.line_style, self.graph_style.line_width, self.graph_style.line_style_number, self.graph_style.mode_number)

                return copy
