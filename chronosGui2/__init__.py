# Import classes and methods
from chronosGui2.animate import MenuToggle
from chronosGui2.animate import delay
from chronosGui2.hardware import Hardware
from chronosGui2.signal_tap import signalTap

# Import top level modules.
import chronosGui2.api as api
import chronosGui2.stats as stats
import chronosGui2.debugger as debugger
import chronosGui2.settings as settings
import chronosGui2.hardware as hardware

# Add the widgets path to import, because PyQt5 calculates the import 
# path out of our control, and we can't directly import them from a
# subfolder like we can with the screens.
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/widgets')

# Import submodules.
import chronosGui2.input_panels
