#!/usr/bin/python3
#From https://stackoverflow.com/questions/38142809/pyqt-5-6-connecting-to-a-dbus-signal-hangs

import sys

from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QApplication
from PyQt5.QtDBus import QDBusConnection, QDBusMessage


class DbusTest(QObject):

    def __init__(self):
        super(DbusTest, self).__init__()
        bus = QDBusConnection.systemBus()
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