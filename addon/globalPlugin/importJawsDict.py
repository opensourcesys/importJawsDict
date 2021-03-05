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

# Constants
_TESTING_MODE = True

import globalPluginHandler
import globalVars
import gui
import wx
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


class DictionaryChooserPanel(wx.Panel):
	"""Generates a wx.Panel containing elements for choosing a Jaws dictionary."""

	def __init__(self, parent=None, id=wx.ID_ANY) -> None:
		super().__init__(parent, id)
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: label of an edit field in Setup Import dialog to enter the path of a Jaws dictionary
		sizer.Add(wx.StaticText(self, wx.ID_ANY, label=_("&Jaws dictionary path:")))
		self.jDict = wx.TextCtrl(self, wx.ID_ANY)
		sizer.Add(self.jDict)


class SetupImportDialog(wx.Dialog):
	"""Creates and populates the import setup dialog."""

	def __init__(self, parent: Any, id: int, title: str) -> None:
		super().__init__(parent, id, title=title)
		self.mainSizer = wx.BoxSizer(wx.VERTICAL)
		# Dictionary options
		choices = (
			# Translators: a reference to the NVDA Default speech dictionary
			_("Default"),
			# Translators: a reference to the NVDA Temporary speech dictionary
			_("Temporary"),
			# Translators: a reference to the NVDA Voice-specific speech dictionary
			_("Voice-specific")
		)
		# NVDA speech dictionary selector
		self.targetDict = wx.RadioBox(self, wx.ID_ANY, choices=choices, style=wx.RA_VERTICAL)
		self.targetDict.Bind(wx.EVT_RADIOBOX, self.onTargetDict)
		# In production we default to the Default dictionary, but in testing we default to Temporary
		if _TESTING_MODE:
			self.targetDict.SetSelection(1)  # Default to the Temporary dictionary
		else:
			self.targetDict.SetSelection(0)  # Default to the default dictionary
		# File chooser
		self.container = wx.Panel(parent=self)
		self.panel = DictionaryChooserPanel(parent=self.container)
		# Setup the buttons
		buttons = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL | wx.HELP)
		# Build the dialog
		self.mainSizer.Add(self.container)
		self.mainSizer.Add(self.targetDict)
		self.mainSizer.Add(buttons, flag=wx.BOTTOM)
		self.mainSizer.Fit(self)
		self.SetSizer(self.mainSizer)
		self.Center(wx.BOTH | WX_CENTER)
		# Button configuration
		ok = wx.FindWindowById(wx.ID_OK, self)
		ok.Bind(wx.EVT_BUTTON, self.onOk)
		help = wx.FindWindowById(wx.ID_HELP, self)
		help.Bind(wx.EVT_BUTTON, self.onHelp)

	def onHelp(self) -> None:
		"""Shows a dialog with a help message to the user."""
		ui.message("Not yet implemented. Try again later.")
		log.debug("Unimplemented help button pressed.")

	def onOk(self) -> None:
		ui.message("It would have been okay, had this been implemented.")
		log.debug("Unimplemented OK button pressed.")


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
		"""Instantiates and manages the import setup dialog."""
		evt.Skip()  # FixMe: document why this is here
		# Translators: title of the import setup dialog
		title = _("Setup your Jaws Dictionary Import")
		dlg = SetupImportDialog(parent=gui.mainFrame, id=wx.ID_ANY, title=title)
