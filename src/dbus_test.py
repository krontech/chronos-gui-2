# -*- coding: future_fstrings -*-

import sys

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QApplication
from PyQt5.QtDBus import QDBusConnection, QDBusMessage


class DbusTest(QObject):

    def __init__(self):
        super(DbusTest, self).__init__()
        bus = QDBusConnection.systemBus()
        bus.registerObject('/', self)
        bus.connect(
            'org.freedesktop.DBus',
            '/org/freedesktop/DBus',
            'org.freedesktop.DBus',
            'NameAcquired',
            self.testMessage
        )
        print('Connected')

    @pyqtSlot(QDBusMessage)
    def testMessage(self, msg):
        print(msg)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    discoverer = DbusTest()
    sys.exit(app.exec_())