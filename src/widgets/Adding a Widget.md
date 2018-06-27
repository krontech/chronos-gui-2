# Adding a Widget

1. Duplicate a minimal existing widget by renaming the files `«my_name».py` and `«my_name»_plugin.py`. (For example, the button.)

2. In `«my_name»_plugin.py»`:
	- change the import, `«my_name» import «MyName»`
	- change the class name, `«MyNamePlugin»`
	- update the `super()` call in `__init__`
	- change the return in `createWidget`
	- change the return in `name`
	- change the designer icon url
	- fix up toolTip and whatsThis
	- (Optionally?) Fix up `domXml`
	- change the return in `includeFile`

3. In `«my_name.py`:
	- change the class name, `«MyName»`, and the widget type if needed
	- update the `super()` call in `__init__`
	
4. Create a quick, identifiable 22×22px icon in `~assets/images/qt_creator_icons/` for Qt Creator/Designer.

Note: Generally, it is a good idea to avoid domXml in favour of stylesheets because domXml gets copied into each instance of the widget. This makes it hard to change the values later.