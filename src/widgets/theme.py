"""Themes for Krontech widgets.
	
	This explicitly does not use QPalettes, because the documentation says:
	
		Warning: Do not use this function in conjunction with Qt Style Sheets. When
		using style sheets, the palette of a widget can be customized using the
		"color", "background-color", "selection-color", "selection-background-color"
		and "alternate-background-color".
		— https://doc.qt.io/qt-5/qwidget.html#palette-prop
	
	Instead, each widget has its own stylesheet, which uses string concatenation
	to use these colours.
	
	This is because, the first time around, I copied what we already had which
	was pretty much black-on-while, and amplified it to only black-on-white to
	try to enhance sunlight readability. This done, all our widgets were made
	without thought to cosmetic theming, with the idea being that we could go
	back and read out colours from the set palette. That would have worked
	extra-nicely, because palettes are inheritable and QSS - while it can be -
	should *not* be because that rapidly becomes an unmaintainable mess. Imagine
	trying to debug a website with crappy, non-scoped CSS but without having the
	dev tools to go in and see which selectors matched which element.

"""


class __light():
	background          = 'white'                 #*screen* background color
	backgroundInEditor  = 'rgba(255,255,255,127)' #screen background color in Qt Designer
	bgBorderInEditor    = 'white'                 #*screen* background border in Qt Designer
	base                = 'white'                 #*widget* background color
	baseInEditor        = 'rgba(255,255,255,127)' #widget background in Qt Designer
	baseActive          = 'rgb(240,240,240)'      #widget active background color (pressed button)
	border              = 'black'                 #*interactive* widget border
	text                = 'black'                 #normal text, buttons, labels, etc.
	textActive          = 'black'                 #normal text, buttons, labels, etc.
	dimText             = '#777'                  #disabled/placeholder text
	subheaderText       = 'black'                 #only for the subheader widget
	headerText          = 'black'                 #only for the header widget
	highlight           = '#777'                  #selected text background
	highlitText         = 'white'                 #selected text letters
	focusRing           = 'blue'                  #activate with jog wheel, shows active widget
	
	

class __dark():
	background         = '#333'                  #*screen* background color
	backgroundInEditor = 'rgba(48,48,48,127)'    #screen background color in Qt Designer
	bgBorderInEditor   = '#333'                  #*screen* background border in Qt Designer
	base               = '#333'                  #*widget* background color
	baseInEditor       = 'rgba(48,48,48,127)'    #widget background in Qt Designer
	baseActive         = 'rgb(96,96,96)'         #widget active background color (pressed button)
	border             = '#fff'                  #*interactive* widget border
	text               = '#fff'                  #normal text, buttons, labels, etc.
	textActive         = '#fff'                  #normal text, buttons, labels, etc.
	dimText            = '#aaa'                  #disabled/placeholder text
	subheaderText      = '#fff'                  #only for the subheader widget
	headerText         = '#fff'                  #only for the header widget
	highlight          = '#777'                  #selected text background
	highlitText        = '#ddd'                  #selected text letters
	focusRing          = 'blue'                  #activate with jog wheel, shows active widget
	
	



def theme(themeName: str) -> __light:
	"""Look up a named theme, 'light' or 'dark'."""
	if themeName == 'light':
		return __light
	elif themeName == 'dark':
		return __dark
	else:
		raise ValueError('No theme named ' + themeName)