# -*- coding: future_fstrings -*-

from math import floor

from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import QLabel, QWidget

from theme import theme
import chronosGui2.settings as settings
from chronosGui2.debugger import *; dbg
#from chronosGui2.animate import delay

class ToasterNotificationQueue(QWidget):
	"""The manager class that sets up and animates the toast
		notifications. Use notify([severity], [timeout],
		message) to add a new notification. On screen
		transition, any transient notifications (those with
		a timeout) will be cleared.
	"""
	
	MESSAGE_HEIGHT = 15
	MESSAGE_BORDER = 1
	MESSAGE_LINE_HEIGHT = 20
	screenHidden = pyqtSignal()
	
	def __init__(self, parent):
		super().__init__(parent)
		
		self.setAttribute(Qt.WA_TransparentForMouseEvents)
		self.setFocusPolicy(Qt.NoFocus)
		
		margin = (80, 20)
		parentGeometry = parent.geometry()
		self.setGeometry( #Center widget.
			parentGeometry.x() + margin[0],
			parentGeometry.y() + margin[1],
			parentGeometry.width() - (margin[0] * 2),
			parentGeometry.height() - (margin[1] * 2),
		)
		
		self._messages = []
	
	class _ToasterNotification(QLabel):
		closed = pyqtSignal()
		timedOut = pyqtSignal()
		
		def __init__(self, parent, severity, timeout, message):
			super().__init__(parent)
			self.severity = severity
			self.laidOut = False
			
			self.theme = theme('dark')
			settings.observe('theme', 'dark', lambda name: (
				setattr(self, 'theme', theme(name)),
				self.refreshStyle(),
			))
			
			if timeout > 0:
				QTimer.singleShot(timeout * 1000, self.timedOut.emit)
			
			self.setText(severity + ': ' + message)
			self.show()
			
		def refreshStyle(self):
			self.setStyleSheet(f"""
				border: {ToasterNotificationQueue.MESSAGE_BORDER}px solid {self.theme.border};
				border-radius: {
					floor(ToasterNotificationQueue.MESSAGE_HEIGHT/2) + 
					ToasterNotificationQueue.MESSAGE_BORDER*2 +
					1
				}; /*Can't use 50%, it just… doesn't work. 😑 Calculate it, nfi where the last 1 comes from but it results in a perfect lozenge at the moment.*/
				padding-right: 0px;
				padding-left: 10px;
				font-size: 16px;
				background: {self.theme.text};
				color: {self.theme.base};
			""")
	
	def notify(*args):
		"""Pops up a little toaster notification near a
			screen edge.
			
			Args:
				optional severity (str): One of 'error'
					(default), 'warning', or 'notification', in
					order of decending severity. Basically,
					"something is not working", "something is
					working but probably not as you intended",
					and "something is working as intended which
					you should know about". For example, if the
					API returns an error internally, it should
					be communicated on through to the UI to aid
					debugging. There's not much we can do about
					it, it is an error. On  the other hand, if
					we're on the main screen and shutter gating
					is enabled but no signal incoming, then we
					will see only a black video feed. To give
					the operator a fighting chance, we should
					warn them that they have turned on this
					trigger, and that video isn't going to work
					until they feed it a signal or disable
					shutter gating. Finally, we issue a
					notification in the case that the operator
					has pressed the save button without marking
					a region for saving, explaining that they
					must mark a region to save before saving.
				optional timeout (int): Time, in seconds, to
					display the notification for. A value of -1
					indicates the toast notification is not
					transient, and can not be dismissed. A
					value of 0 indicates the notification is
					transient, and can be dismissed (or cleared
					when the screen is left), but will not time
					out. This defaults to 10 seconds for
					warnings and notifications, and 0 seconds 
					for errors because they are important.
				message (str): The text to be displayed in the
					toast notification.
		"""
		
		notification = args[0]._ToasterNotification(
			args[0],
			{'error':'error', 'warning':'warning', 'notification':'notification'} #Severity level whitelist.
				[(['error'] + list([t for t in args if type(t) is str]))[-2]],
			(list([t for t in args if type(t) is int]) + [10])[0],
			[t for t in args if type(t) is str][-1]
		)
		notification.setGeometry(0,0,
			args[0].width(), type(args[0]).MESSAGE_LINE_HEIGHT )
		args[0]._messages.append(notification)
		args[0].layOutMessages()
		
		notification.closed.connect(  lambda: args[0].removeMessage(notification))
		notification.timedOut.connect(lambda: args[0].removeMessage(notification))
	
	
	def removeMessage(self, message):
		message.deleteLater()
		self._messages.remove(message)
		self.layOutMessages()
	
	
	def layOutMessages(self):
		if self._messages:
			self.show()
		else:
			self.hide()
		
		for slot, message in enumerate(self._messages):
			message.setGeometry(
				0,
				slot * type(self).MESSAGE_LINE_HEIGHT,
				message.width(),
				message.height()
			)