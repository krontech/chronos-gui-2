# Makefile to build generated code.
PYDIR := $(dir $(lastword $(MAKEFILE_LIST)))/..
VPATH := $(PYDIR)/forms
SRCDIR := $(PYDIR)/..
.DEFAULT_GOAL := all

UICFLAGS = --import-from chronosGui2.generated

# The things we want to build and their dependencies.
assets.qrc: $(shell find $(SRCDIR)/assets -type d)

UISRC := $(shell find $(PYDIR)/forms -name '*.ui' -printf '%P\n')
UIMOD := $(shell find $(PYDIR)/forms -mindepth 1 -type d -printf '%P\n')
PYGENERATED := $(UISRC:.ui=.py)
PYGENERATED += $(addsuffix /__init__.py, $(UIMOD))
PYGENERATED += assets_rc.py
PYGENERATED += __init__.py

# Special rule to build the top-level __init__ file.
# FIXME: it doesn't really depend on the files, only their names.
__init__.py: $(filter-out $(addsuffix /%.ui, $(UIMOD)), $(UISRC))
	@echo "Generating $@"
	@echo "from chronosGui2.generated.version import __version__" > $@
	@echo $(^F:.ui=) | xargs -n1 printf "from chronosGui2.generated.%s import *\n" >> $@
	@echo "" >> $@
	@echo "# UI Modules" >> $@
	@echo $(UIMOD) | xargs printf "import chronosGui2.generated.%s\n" >> $@

# Generic rule for building a UI module __init__ file.
%/__init__.py:
	@echo "Generating $@"
	@echo $(^F:.ui=) | xargs -n1 printf "from chronosGui2.generated.$(*).%s import *\n" > $@

# Generate dependencies for each of the UI modules.
$(foreach modname, $(UIMOD), $(modname)/__init__.py: $(filter $(modname)/%.ui, $(UISRC)))

# Special rule to generate the module version dynamically, but
# only if we happen to be in a git working tree. Otherwise, we
# should leave the version file alone.
ifeq ($(shell git rev-parse --is-inside-work-tree 2>/dev/null),true)
PYGENERATED += version.py

.PHONY: version.py
version.py:
	@echo "Generating $@"
	@echo __version__ = \"$(shell git describe --tags --always)\" > $@
endif

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
%.py: %.ui
	@[ -d $(@D) ] || mkdir -p $(@D)
	pyuic5 $(UICFLAGS) -o $@ $^

all: assets_rc.py assets.qrc $(PYGENERATED)

clean:
	rm -rf $(PYGENERATED)
	rm -rf $(UIMOD)
	rm -rf assets.qrc
