from PyQt5.QtCore import Qt

class FocusablePlugin():
	"""Some behaviour to make focussable widgets work correctly.
	
		Touch and jog wheel have subtly different requirements. Jog wheel can
		focus in to a widget and then have sub-focusses, for example.
	"""
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self.setFocusPolicy(Qt.NoFocus)