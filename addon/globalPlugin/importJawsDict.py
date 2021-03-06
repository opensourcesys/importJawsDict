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

import globalPluginHandler
import globalVars
import gui
import wx
import ui
import config
from scriptHandler import script
from logHandler import log

try:#dbg
	addonHandler.initTranslation()
	log.debug("#dbg. initiated translation.")
except:#dbg
	log.debug("#dbg. Failed to initTranslation.")

#: importJawsDict Add-on config database
#config.conf.spec["importJawsDict"] = {
	#"lastPath": "boolean(default=False)",
	#"lastFile": "boolean(default=False)",
#}

class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	#: Contains the path of the last dictionary opened
	lastPath = None
	#: Contains the name of the last dictionary file opened
	lastFile = None

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
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onSetupImportDialog, self.toolsMenuItem)
		log.debug("#dbg. Finished __init__ of globalPlugin.")

	def terminate(self):
		"""Cleans up the dialog(s)."""
		log.debug("#dbg. Terminating.")
		super(GlobalPlugin, self).terminate()
		log.debug("#dbg. Terminating, but made it past super terminate.")
		# Check whether running in secure mode, and exit if so
		if globalVars.appArgs.secure:
			return
		try:
			self.toolsMenu.Remove(self.toolsMenuItem)
		except (RuntimeError, AttributeError):
			log.debug("Could not remove the Import Jaws Dictionary menu item.")

	def onSetupImportDialog(self, evt):
		"""Instantiates and manages the import setup dialog."""
		log.debug("#dbg. In onSetupImportDialog.")
		ui.browseableMessage("At least get the bloody menu item working!\nPlease! I'm begging!")#dbg
		return #dbg

	@script(
		gesture="kb:alt+NVDA+a",
		# Translators: description of the toggle gesture for keyboard help
		description=_("Launches the nuclear wessles!"),
	)
	def script_doNothingUseful(self, gesture):
		ui.message("Maybe she's talking to that man!")
		log.debug("#dbg. In the script."))

