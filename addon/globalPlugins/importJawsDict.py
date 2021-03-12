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

import wx
import gui
import ntpath
import re
import contextlib
from collections import deque

import addonHandler
import globalPluginHandler
import globalVars
import ui
import config
from logHandler import log

try:#dbg
	addonHandler.initTranslation()
except:#dbg
	log.debug("#dbg. Failed to initTranslation.")

#: importJawsDict Add-on config database
config.conf.spec["importJawsDict"] = {
	"lastPath": "boolean(default=False)",
	"lastFile": "boolean(default=False)",
}

class SpeechDictItem:
	"""Objects of this class represent a single dictionary item during the transition from JDF to NVDA.
	It is intended to be initialized with a JDF item, and to organize itself appropriately for an NVDA
	dictionary item. It is expected that these will be used in an iterated deque or list.

	For reference, the JDF record spec is:
	Each record begins and ends with a separator. The separator is a punctuation such as ".", ",", "!",
	or maybe others--Jaws seems to look for punctuation missing from the actual or replacement words.
	That same separator is then used to separate the other fields on the line.
	If * appears in the first field, it represents a wildcard within a whole word context. (unconfirmed!)
	If a * appears in the third through fifth fields, it represents any value.
	The fields are:
	Actual word
	Replacement word
	Language (known codes below)
	Synthesizer
	Voice
	Output Language (0 is default)
	Case sensitive (0: False, 1: True)
	Known input word languages:
	*: any
	0x07: German
	0x09: English
	0x10: Italian
	0x16: Portuguese
	0x0a: Spanish
	0x0b: Finnish
	0x0c: French
	"""

	#: Constant containing a regular expression used for verifying and splitting JDF rules
	RECORD_EXP = re.compile(
		# The field separator. Hereinafter: \1
		r"^(.)"
		# inWord: The word that is being pronounced incorrectly
		r"(?P<inWord>.+[^\1])\1"
		# outWord: The word that should be spoken
		r"(?P<outWord>.+[^\1])\1"
		# lang: Contains the code for the language specified in the JDF rule, or *
		r"(?P<lang>[0-9a-zA-Z\*]+)\1"
		# synth: Contains the name of any synthesizer the JDF specifies for this rule
		r"(?P<synth>.+[^\1])\1"
		# voice: Contains the name of any synthesizer voice the JDF specifies for this rule
		r"(?P<voice>.+[^\1])\1"
		# outLang: we ignore the output language
		r"(?:[0-9\*]+)\1"
		# case: An int (later boolean) specifying whether the inWord is case sensitive
		r"(?P<case>[01])\1$"
	)

	def __init__(self, jdfLine: str = None) -> None:
		"""Creates a DictItem object.
		jdfLine: a line taken directly from a JDF file, with no start/end whitespace.
		""" # FixMe: needs a proper docstring. Needs proper kwargs.
		self.isValid = False  # Fixed by self.process(), if validity is deserved
		self.parseJDFLine(jdfLine)
		# However it gets setup (only one way currently), we need to process the values.
		self.process()

	def parseJDFLine(self, line: str) -> None:
		"""Takes a line from a JDF file, and assigns its various fields to this object's vars.
		If what it receives is None, it raises an AttributeError.
		If it receives text that is a comment, or doesn't parse as a JDF record, it raises a ValueError.
		"""
		# Sanity check
		if line is None:
			raise AttributeError("None is not a valid JDF line.")
		# Match the line against the format of a valid record.
		# All JDF lines must start, contain repeatedly, and end with, their field separator.
		# This also gets the groups, for later processing.
		record = RECORD_EXP.fullmatch(strip(line))
		if record is None:
			raise ValueError(f"The provided line ({line}), doesn't match the format of a proper record.")
		# Process the record into this object
		log.debug(f"#dbg. Line: {line}")
		for field, value in record.groupdict().values():
			log.debug(f'#dbg. Setting self.{field} to "{value}"')
			setattr(self, field, value)

	def process(self) -> None:
		"""Once the object has been setup, this makes its values useful.
		Reshapes provided values to be Pythonic and NVDAish.
		Does any other kind of processing necessary to make the values useful.
		Should be called last before the object is stored.
		Raises ValueError for any unset or incorrect values.
		"""
		log.debug(f"#dbg. Processing: {self.__dict__}")
		# Comments with each conditional explain what we're looking for.
		self.isValid = False
		# Needs to contain at least one character
		if self.inWord is None or len(self.inWord) < 1:
			raise ValueError('Record has no "in" word.')
		if self.outWord is None:
			raise ValueError('Record has no "out" word.')
		# Removes any sound related XML from the outWord, then checks length
		self.outWord = re.sub(r"<sound +.*?/>", "", self.outWord, flags=re.IGNORECASE)
		if len(self.outWord) < 1:
			raise ValueError('After processing, record has no "out" word.')
		with contextlib.suppress(AttributeError):  # Some of these might be unset, but we don't care
			# If language is empty or set to any (*), set it to None
			if self.lang == "" or self.lang == "*":
				self.lang = None
			# if synth is empty or set to any (*), set it to None
			if self.synth == "" or self.synth == "*":
				self.synth = None
			# If voice is empty or set to any (*), set it to None
			if self.voice == "" or self.voice == "*":
				self.voice = None
			# Case is either 0 (False), 1 (True), "" (False), or None. Make it a bool instead
			if self.case is not None and self.case == "1":
				self.case = True
			else:
				self.case = False
		# The processing is done. If we got this far, we have a valid object.
		self.isValid = True
		log.debug(f"#dbg. Processed: {self.__dict__}")


# Not currently used
class DictionaryChooserPanel(wx.Panel):
	"""Generates a wx.Panel containing elements for choosing a Jaws dictionary."""

	def __init__(self, parent=None, id=wx.ID_ANY) -> None:
		super().__init__(parent, id)
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: label of an edit field in Setup Import dialog to enter the path of a Jaws dictionary
		sizer.Add(wx.StaticText(self, wx.ID_ANY, label=_("&Jaws dictionary path:")))
		self.jDict = wx.TextCtrl(self, wx.ID_ANY)
		sizer.Add(self.jDict)

# Not currently used
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

class UserCanceled(Exception):
	"""A simple exception which is raised if the user cancels a multi step dialog."""
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
		self.outWordolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
		self.outWordolsMenuItem = self.outWordolsMenu.Append(
			wx.ID_ANY, kind=wx.ITEM_NORMAL,
			# Translators: item in the NVDA Tools menu to open the Jaws dictionary import dialog
			item=_("Import &Jaws Dictionary..."),
			# Translators: tooltip for the "Import Jaws Dictionary" Tools menu item
			helpString=_("Import a Jaws speech dictionary into an NVDA speech dictionary")
		)
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onMultiStepImport, self.outWordolsMenuItem)
		log.debug("#dbg. Finished __init__ of globalPlugin.")

	def terminate(self):
		"""Cleans up the dialog(s)."""
		log.debug("#dbg. Terminating.")
		super(GlobalPlugin, self).terminate()
		# Check whether running in secure mode, and exit if so
		if globalVars.appArgs.secure:
			return
		try:
			self.outWordolsMenu.Remove(self.outWordolsMenuItem)
		except (RuntimeError, AttributeError):
			log.debug("Could not remove the Import Jaws Dictionary menu item.")

	def onMultiStepImport(self, evt):
		"""Manages the user interaction dialogs and workflow."""
		evt.Skip()  # FixMe: document why this is here
		# Each of these has the potential to be cancelled by the user, which will raise UserCancelException
		# Additionally, it was convenient to handle FileNotFoundError at this level.
		try:
			# FixMe: there should be a text dialog here explaining to the user what's about to happn.
			# Step 1: get the source dictionary
			file = self.askForSource()
			# Step 2: get the target dictionary
			#: An int that is an index into self.NVDA_DICTS
			targetDict = self.askForTarget()
			# Import from the selected file and handle the result
			self.importFromFile(file)
			# Determine which stats dialog to show, based on line count to record count comparison
			if self.lineCount == self.recordCount:
				self.confirmImportSimple(path + file)  # All lines are records
			elif self.lineCount > self.recordCount:
				self.confirmImportWithBads(path + file)  # Some lines aren't records
		except UserCanceled:
			return
		except (FileNotFoundError, IOError) as fnf:
			log.debug(f"#dbg. Got a file not found error for: {path}{file}")
			return  # FixMe: need real dialog code here

	def askForSource(self) -> str:
		"""Shows a file chooser dialog asking for a Jaws dictionary.
		Raises UserCancelException if the user cancels.
		Returns a string containing the path of the file chosen.
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
				raise UserCancelException
			else:
				# Return the selected file
				return ntpath.normpath(sourceChooser.GetPath())

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

	def importFromFile(self, pathAndFile: str) -> None:
		"""Reads the JDF. Installs it into self.importables.
		Also stores bad records in self.unimportables, and generates self.lineCount and self.recordCount.
		Has the slight potential to raise FileNotFoundError.
		Accepts the path and filename of the JDF.
		""" # FixMe: needs a better docstring
		log.debug(f'#dbg. In importFromFile("{pathAndFile})')
		#: Holds the list of validated speech dict entries
		self.importables: deque = deque()
		#: Holds the list of rejected lines
		self.unimportables: list = []
		#: Holds the count of lines found, no matter their disposition
		self.lineCount: int = 0
		#: Holds the count of successfully discovered records
		self.recordCount: int = 0
		# Open the JDF
		with open(pathAndFile, "r", encoding="utf-8") as jdf:
			# Iterate each line of the file
			for line in jdf:
				self.lineCount += 1
				# Attempt to put the line in the deque of records
				try:
					self.importables.Append(SpeechDictItem(line))
					self.recordCount += 1
				except ValueError:  # Raised if the line's format wasn't a record
					unimportables.Append(line)  # Add it to the list to be handled later

	def confirmImportSimple(self, pathAndFile: str) -> None:
		"""Displays stats to the user on successful file read. Confirms continuance."""
		with wx.MessageDialog(
			gui.mainFrame,
			# Translators: a message to the user showing stats, and asking whether to continue
			_(
				"Successfully found {0} Jaws speech dictionary records, in {1} lines from the file {2}.\n"
				"Continue if that's what you expected, and you're ready to import them into NVDA's {3}.\n"
			).format(self.recordCount, self.lineCount, pathAndFile, self.NVDA_DICTS[self.targetDict]),
			# Translators: title of the Found Records Dialog
			caption=_("Step 3: Confirm Import"),
			style=wx.OK|wx.CANCEL
		) as confirmationDialog:
			# Translators: Re-label the "OK" button as "Continue"
			confirmationDialog.SetOKLabel("&Continue")
			# Show the dialog, and check for cancel
			if confirmationDialog.ShowModal() == wx.ID_CANCEL:
				raise UserCancelException
			else:
				return

	def confirmImportsWithBads(self, pathAndFile: str) -> None:
		"""Shows the import statistics in cases where there was a lines to records mismatch.
		Asks the user whether to continue, cancel, or show the difficult lines.
		"""
		with wx.MessageDialog(
			gui.mainFrame,
			# Translators: message to the user with statistics and options
			_(
				"Out of {0} lines in file {1},\n"
				"only {2} of them were recognized as valid Jaws speech dictionary entries.\n"
				"\nYou can import those {2} records into NVDA's {3},\n"
				"you can review the lines that weren't recognized then decide what to do,\n"
				"or you can cancel the import."
			).format(self.lineCount, pathAndFile, self.recordCount, self.NVDA_DICTS[self.targetDict]),
			# Translators: title of the Found Records Dialog
			caption=_("Step 3: Confirm or Review Import"),
			style=wx.YES_NO|wx.CANCEL|wx.NO_DEFAULT
		) as confirmationDialog:
			# FixMe: this should react to False by showing a less user friendly, but meaningful, message
			confirmationDialog.SetYesNoLabels(
				# Translators: re-label the "Yes" button as "Review"
				_("&Review"),
				# Translators: re-label the "No" button as "Continue"
				_("&Continue")
			)
			result = confirmationDialog.ShowModal()
		if result == wx.ID_CANCEL:
			raise UserCancelException
		elif result == wx.ID_NO:  # Continue was clicked
			return
		# Else Review was clicked
		# Translators: an explanatory HTML message to the user about dealing with the list of bad entries
		msg = _(
			"<p>Below you will find a list of {0} entries which were found in the file {1}, "
			"but which were not recognized as Jaws speech dictionary records.<br/>\n"
			"You can use normal Windows controls to select and copy these to the clipboard, so you can "
			"save them in a file to try to fix them later, if they are supposed to be valid entries.</p>\n"
			"<p>You may also <a href=\"mailto:luke@newanswertech.com\">email them</a> to the add-on authors"
			" to review, if you think this is a bug or that these entries should have been recognized.</p>\n"
			"<p>To return to the import, press Alt+F4 to close this window.</p>\n&nbsp;<br/>\n<hr>\n<pre>\n"
		).format(self.lineCount - self.recordCount, pathAndFile)
		# Add each of the bad lines to the message
		for line in self.unimportables:
			msg += line + "\n"
		msg += "</pre>"
		# FixMe: eventually I would like to use some better kind of dialog for this.
		ui.browseableMessage(
			msg, isHtml=True,
			# Translators: title of the dialog containing the list of JDF lines which couldn't be imported
			title=_("Review Dictionary Entries That Can't Be Imported, Alt+F4 when done")
		)

	# Unused code
	def onSetupImportDialog_old(self, evt):
		"""Instantiates and manages the import setup dialog."""
		log.debug("#dbg. In onSetupImportDialog.")
		evt.Skip()  # FixMe: document why this is here
		# Translators: title of the import setup dialog
		title = _("Setup your Jaws Dictionary Import")
		dlg = SetupImportDialog(parent=gui.mainFrame, id=wx.ID_ANY, title=title)
		dlg.show()
