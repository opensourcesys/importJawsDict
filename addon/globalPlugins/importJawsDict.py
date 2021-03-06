# Import Jaws Dictionary (importJawsDict.py), version 0.X-dev
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

import ntpath
import wx
import gui

import globalPluginHandler
import globalVars
import ui
import config
from logHandler import log

try:#dbg
	addonHandler.initTranslation()
	log.debug("#dbg. initiated translation.")
except:#dbg
	log.debug("#dbg. Failed to initTranslation.")

#: importJawsDict Add-on config database
config.conf.spec["importJawsDict"] = {
	"lastPath": "boolean(default=False)",
	"lastFile": "boolean(default=False)",
}


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

	def __init__(self, parent, id: int, title: str) -> None:
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
			log.debug("#dbg. Using temp dictionary while in testing mode.")
			self.targetDict.SetSelection(1)  # Default to the Temporary dictionary
		else:
			self.targetDict.SetSelection(0)  # Default to the default dictionary
			log.debug("#dbg. Using default dictionary since not in testing mode.")
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
		log.warng("Unimplemented help button pressed in SetupImportDialog.")

	def onOk(self) -> None:
		ui.message("It would have been okay, had this been implemented.")
		log.warng("Unimplemented OK button pressed in SetupImportDialog.")

#: A simple exception which is raised if the user cancels a multi step dialog
class UserCanceled(Exception):
	pass

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	#: Constant tuple of the NVDA speech dictionaries
	NVDA_DICTS = (
		# Translators: a reference to the NVDA Default speech dictionary
		_("Default dictionary"),
		# Translators: a reference to the NVDA Voice-specific speech dictionary
		_("Voice dictionary"),
		# Translators: a reference to the NVDA Temporary speech dictionary
		_("Temporary dictionary")
	)

	#: Contains the path of the last dictionary opened
	lastPath = ""
	#: Contains the name of the last dictionary file opened
	lastFile = ""

	def __init__(self):
		"""Initializes the add-on by performing the following tasks:
		- Checks whether running in secure mode, and stops running if so.
		- Establishes the entry on the NVDA Tools menu.
		"""
		log.debug("#dbg. In globalPlugin.__init__")
		super(GlobalPlugin, self).__init__()
		log.debug("#dbg. After super call in __init__ of globalPlugin.")
		# Stop initializing if running in secure mode
		if globalVars.appArgs.secure:
			log.debug("#dbg. Running in secure mode, bailing.")
			return
		else: #dbg
			log.debug("#dbg. Not running in secure mode. Anti-bailing.")
		# Create an entry on the NVDA Tools menu
		self.toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
		self.toolsMenuItem = self.toolsMenu.Append(
			wx.ID_ANY, kind=wx.ITEM_NORMAL,
			# Translators: item in the NVDA Tools menu to open the Jaws dictionary import dialog
			item=_("Import &Jaws Dictionary..."),
			# Translators: tooltip for the "Import Jaws Dictionary" Tools menu item
			helpString=_("Import a Jaws speech dictionary into an NVDA speech dictionary")
		)
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onMultiStepImport, self.toolsMenuItem)
		log.debug("#dbg. Finished __init__ of globalPlugin.")

	def terminate(self):
		"""Cleans up the dialog(s)."""
		log.debug("#dbg. Terminating.")
		super(GlobalPlugin, self).terminate()
		# Check whether running in secure mode, and exit if so
		if globalVars.appArgs.secure:
			return
		try:
			self.toolsMenu.Remove(self.toolsMenuItem)
		except (RuntimeError, AttributeError):
			log.debug("Could not remove the Import Jaws Dictionary menu item.")

	def onMultiStepImport(self, evt):
		"""Instantiates and manages the user interaction dialogs."""
		evt.Skip()  # FixMe: document why this is here
		# Each of these has the potential to be cancelled by the user, which will raise UserCancelException
		try:
			# FixMe: there should be a text dialog here explaining to the user what's about to happn.
			# Step 1: get the source dictionary
			path, file = self.askForSource()
			# Step 2: get the target dictionary
			#: An int that is an index into self.NVDA_DICTS
			targetDict = self.askForTarget()
		except UserCanceled:
			return

	def askForSource(self):
		"""Shows a file chooser dialog asking for a Jaws dictionary.
		Raises UserCanceled if the user cancels.
		Returns a tuple containing the path and filename.
		"""  # FixMe: proper docstring needed
		with wx.FileDialog(
			gui.mainFrame,
			# Translators: the title of the Jaws dictionary file selector dialog.
			_("Step 1: select a Jaws dictionary"),
			self.lastPath, self.lastFile,
			wildcard="Jaws Dictionary Files (*.jdf)|*.jdf|All files (*.*)|*.*",
			style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST
		) as sourceChooser:
			# Show the dialog and react to cancel
			if sourceChooser.ShowModal() == wx.ID_CANCEL:
				raise UserCanceled
			else:
				# Return the selected path and file
				return ntpath.split(ntpath.normpath(sourceChooser.GetPath()))

	def askForTarget(self):
		"""Shows a dialog with a list of possible NVDA dictionaries for the user to choose from.
		Raises UserCanceled if the user does.
		Returns the result (an index into self.NVDA_DICTS).
		""" # FixMe: needs a real docstring
		# Ask the user which dictionary to use
		with wx.SingleChoiceDialog(
			gui.mainFrame,
			# Translators: the descriptive message shown to the user, asking
			# which target NVDA dictionary they wish to use.
			_(
				"Step 2: select the target NVDA dictionary where you would like "
				"the entries from the Jaws dictionary to be placed."
			),
			# Translators: the title of the NVDA dictionary selector dialog
			_("Choose the target dictionary"),
			self.NVDA_DICTS, wx.OK|wx.CANCEL|wx.CENTRE
		) as targetChooser:
		# In production we default to the Default dictionary, but in testing we default to Temporary
			if _TESTING_MODE:
				targetChooser.SetSelection(2)
			else:
				targetChooser.SetSelection(0)
			# Show the dialog and react to cancel
			if targetChooser.ShowModal() == wx.ID_CANCEL:
				raise UserCanceled
			else:
				return targetChooser.GetSelection()

	def next(self):
		pass
		# Read the dictionary into a variable
		#try:
			#with open(path, "r") as dictFile:
				# Do something
				#except IOError:
				# an error

	def onSetupImportDialog_old(self, evt):
		"""Instantiates and manages the import setup dialog."""
		log.debug("#dbg. In onSetupImportDialog.")
		evt.Skip()  # FixMe: document why this is here
		# Translators: title of the import setup dialog
		title = _("Setup your Jaws Dictionary Import")
		dlg = SetupImportDialog(parent=gui.mainFrame, id=wx.ID_ANY, title=title)
		dlg.show()
