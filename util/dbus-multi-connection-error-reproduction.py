import sys, signal
from PyQt5.QtCore import pyqtSlot, QObject, QCoreApplication
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusReply

signal.signal(signal.SIGINT, signal.SIG_DFL) #Quit on ctrl-c.


#First, set up two D-Bus providers.

QDBusConnection.systemBus().registerService(
	'com.krontech.chronos.control.mock' )
QDBusConnection.systemBus().registerService(
	'com.krontech.chronos.video.mock' )

class Provider1(QObject):
	@pyqtSlot(result=str)
	def exampleCall(self):
		return 'I am #1.'

class Provider2(QObject):
	@pyqtSlot(result=str)
	def exampleCall(self):
		return 'I am #2.' #ERROR: This is never called.

provider1 = Provider1()
QDBusConnection.systemBus().registerObject('/', provider1, 
	QDBusConnection.ExportAllSlots )

provider2 = Provider2()
QDBusConnection.systemBus().registerObject('/', provider2, 
	QDBusConnection.ExportAllSlots )

provider1API = QDBusInterface('com.krontech.chronos.control.mock', '/', '',
	QDBusConnection.systemBus() )
provider2API = QDBusInterface('com.krontech.chronos.video.mock', '/', '',
	QDBusConnection.systemBus() )



#Second, call both D-Bus providers.
#Only one provider is actually called.

app = QCoreApplication(sys.argv)

result1 = QDBusReply(provider1API.call('exampleCall')).value()
result2 = QDBusReply(provider2API.call('exampleCall')).value()

service1 = provider1API.service()
service2 = provider2API.service()

print(f"Provider1: '{result1}' on {service1}")
print(f"Provider2: '{result2}' on {service2}") #ERROR: Prints 'I am #1.'

sys.exit(app.exec_())