# Makefile to build generated code.
PYDIR := $(dir $(lastword $(MAKEFILE_LIST)))/..
SRCDIR := $(PYDIR)/..
.DEFAULT_GOAL := all

UICFLAGS = --import-from chronosGui2.generated

# The things we want to build and their dependencies.
assets.qrc: $(shell find $(SRCDIR)/assets -type d)

UISRC := $(shell find $(PYDIR)/forms/ -name '*.ui')
PYGENERATED := $(notdir $(UISRC:.ui=.py))
PYGENERATED += assets_rc.py
PYGENERATED += __init__.py

# Special rule to build the module __init__ file
__init__.py: $(notdir $(UISRC:.ui=.py))
	@echo "Generating $@"
	@echo $(^F:.py=) | xargs -n1 printf "from chronosGui2.generated.%s import *\n" > $@

# Helper function to generate the inner XML for a QResource file.
# Usage: $(call qrc_list_files, <dirname>, <filepattern>)
define qrc_list_files
	(cd $(SRCDIR) && find -L $1 -name $2 -printf '    <file>%h/%f</file>\n')
endef

# Generic rule for building a QResource file.
%.qrc: $(SRCDIR)/%
	@echo "Generating $@"
	@echo "<RCC>" > $@
	@echo "  <qresource>" >> $@
	@$(call qrc_list_files, $*, '*.png') >> $@
	@$(call qrc_list_files, $*, '*.svg') >> $@
	@echo "  </qresource>" >> $@
	@echo "</RCC>" >> $@

# Generic rule for building a Python resource file.
# Unfortunately, pyrcc5 has a very hard time operating out-of-tree
# so we need to create a symlink to the resource directory in the
# source tree. It seems like this should be fixable with the -root
# option, but that doesn't appear to do anything.
%_rc.py: %.qrc
	@[ -e $* ] || ln -s $(SRCDIR)/$* $*
	pyrcc5 -o $@ $^
	@[ -L $* ] && rm $*

# Generic rule for building a Python/Qt UI files.
%.py: $(PYDIR)/forms/%.ui
	pyuic5 $(UICFLAGS) -o $@ $^

all: assets_rc.py assets.qrc $(PYGEN)

clean:
	rm -rf $(PYGENERATED)
	rm -rf assets.qrc
