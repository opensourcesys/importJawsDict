# Import Jaws Dictionary (importJawsDict.py), version 0.1-dev
# A global plugin which provides a tool to import Jaws speech dictionaries into NVDA's dictionaries.
# Written by Luke Davis, based on regular expression development performed by Brian Vogel.

#    Copyright (C) 2021 Open Source Systems, Ltd. <newanswertech@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License
# as published by    the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import globalPluginHandler
import globalVars
import gui
#import wx
import ui
import config
#from scriptHandler import script
from logHandler import log

addonHandler.initTranslation()

#: importJawsDict Add-on config database
config.conf.spec["importJawsDict"] = {
	"lastPath": "boolean(default=False)",
	"lastFile": "boolean(default=False)",
}

class importJawsDictSettings (gui.settingsDialogs.SettingsPanel):
	"""NVDA configuration panel based configurator  for importJawsDict."""

	# Translators: the label for the Import Jaws Dictionary settings category in NVDA Settings screen.
	title = _("Import Jaws Dictionary")

	def makeSettings(self, settingsSizer):
		"""Creates a settings panel."""
		helper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.startInWindowsModeCB = helper.addItem(
			wx.CheckBox(
				self,
				# Translators: label for a checkbox in Import Jaws Dictionary settings panel
				label=_("Start NVDA with the numpad set to Windows nav mode")
			)
		)
		self.startInWindowsModeCB.SetValue(config.conf["importJawsDict"]["startInWindowsMode"])

	def onSave(self):
		config.conf["importJawsDict"]["startInWindowsMode"] = self.startInWindowsModeCB.Value


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	#: Contains the path of the last dictionary opened
	lastPath = None
	#: Contains the name of the last dictionary file opened
	lastFile = None

	def __init__(self) -> None:
		"""Initializes the add-on by performing the following tasks:
		- Checks whether running in secure mode, and stops running if so.
		- Establishes the entry on the NVDA Tools menu.
		"""
		super(GlobalPlugin, self).__init__()
		# Stop initializing if running in secure mode
		if globalVars.appArgs.secure:
			return
		# Create an entry on the NVDA Tools menu
		self.toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
		self.toolsMenuItem = self.toolsMenu.Append(
			wx.ID_ANY,
			# Translators: item in the NVDA Tools menu to open the Jaws dictionary import dialog
			_("Import &Jaws Dictionary..."),
			# Translators: tooltip for the "Import Jaws Dictionary" Tools menu item
			_("Import a Jaws speech dictionary into an NVDA speech dictionary")
		)
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onSetupImportDialog, self.toolsMenuItem)

	def terminate(self) -> None:
		"""Cleans up the dialog(s)."""
		super(GlobalPlugin, self).terminate()
		# Check whether running in secure mode, and exit if so
		if globalVars.appArgs.secure:
			return
		try:
			self.toolsMenu.Remove(self.toolsMenuItem)
		except (RuntimeError, AttributeError):
			log.debug("Could not remove the Import Jaws Dictionary menu item.")

	def onSetupImportDialog(self) -> None:
		