#!/usr/bin/env python2
import sys
import os
import logging
import signal
import argparse
import ConfigParser
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import pyqtRemoveInputHook, QThread
from subprocess import Popen, PIPE, STDOUT
import dbus
import dbus.service
import dbus.glib

DBUS_SESSION = "org.emacs.JabberEl"
DBUS_PATH = "/org/emacs/JabberEl"


class BaseTrayIcon(QtGui.QSystemTrayIcon):

    def createIcon(self, iconFileName, text, text_color, background_color=None,
                   defaultFontSize=9):
        icon = QtGui.QPixmap(16, 16)
        icon.fill(QtGui.QColor(background_color)
                  if background_color else QtCore.Qt.transparent)
        # Create a painter to paint on to the icon
        # and draw on the text
        painter = QtGui.QPainter(icon)
        # painter.setOpacity(0.5)
        # Draw text of temperature
        font = QtGui.QFont('stlarch', defaultFontSize, QtGui.QFont.Black)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(text_color))
        painter.drawPixmap(QtCore.QPoint(0, 0), QtGui.QPixmap(iconFileName))
        painter.setOpacity(1)
        painter.drawText(-1, 12, str(text))
        painter.end()
        # Return the icon
        return QtGui.QIcon(icon)


class MailTrayIcon(BaseTrayIcon):
    iconFileName = '/usr/share/icons/oxygen/16x16/apps/internet-mail.png'
    textColor = "green"
    blink = True
    unread = 0

    def __init__(self, config, parent=None):
        icon = self.createIcon('', '0', self.textColor, 7)
        self.service = JabberTrayService(self)
        QtGui.QSystemTrayIcon.__init__(self, icon, parent)
        self.menu = QtGui.QMenu(parent)
        traySignal = "activated(QSystemTrayIcon::ActivationReason)"
        QtCore.QObject.connect(self, QtCore.SIGNAL(traySignal), self.clear)
        # Create Menu
        clearAction = self.menu.addAction("Clear")
        exitAction = self.menu.addAction("Exit")
        self.setContextMenu(self.menu)
        self.connect(exitAction, QtCore.SIGNAL('triggered()'), self.exit)
        self.connect(clearAction, QtCore.SIGNAL('triggered()'), self.clear)
        self.blink_timer = QtCore.QTimer(self)
        QtCore.QObject.connect(
            self.blink_timer, QtCore.SIGNAL("timeout()"),
            self.blink_timer_timeout)
        self.blink_timer.start(300)
        self.config = config

    def exit(self):
        sys.exit(0)

    def clear(self):
        self.blink = False
        self.unread = 0

    def blink_timer_timeout(self):
        if self.blink:
            self.setIcon(self.createIcon('', self.unread, self.textColor,
                                         background_color='black'))
        elif self.unread:
            self.setIcon(self.createIcon('', self.unread, 'black',
                                         background_color='green'))
        self.blink = not self.blink


class JabberElTray(QtGui.QApplication):

    def __init__(self, argv, config):
        super(JabberElTray, self).__init__(argv)
        self.setQuitOnLastWindowClosed(False)
        self.widget = QtGui.QWidget()
        self.mailIcon = MailTrayIcon(config, self.widget)

    def start(self):
        self.mailIcon.show()


class JabberTrayService(dbus.service.Object):

    def __init__(self, app):
        self.app = app
        bus_name = dbus.service.BusName(
            DBUS_SESSION, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, DBUS_PATH)

    @dbus.service.method(dbus_interface=DBUS_SESSION)
    def activity(self, message):
        logging.debug(message)
        count = 0
        try:
            count = int(message)
        except:
            pass
        self.app.blink = True if count > 0 else False
        self.app.unread = count
        return ""
        # self.app.show()

    @dbus.service.method(dbus_interface=DBUS_SESSION)
    def message(self, frm, buf, text, title):
        logging.debug(frm)
        self.activity(self.app.unread + 1)
        return ""

    @dbus.service.method(dbus_interface=DBUS_SESSION)
    def clear(self):
        self.app.blink = False
        self.app.unread = 0
        # if self.app.unread < 0:
        #    self.app.unread=0
        return ""


def main(args):
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    config = ConfigParser.RawConfigParser()
    home = os.getenv('USERPROFILE') or os.getenv('HOME')
    config.read(os.path.join(home, '.jabberel-tray.cfg'))

    app = JabberElTray(sys.argv, config)
    app.start()
    logging.debug(os.path.dirname(__file__))
    sys.exit(app.exec_())

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--exit', default=False, action="store_true",
                        help='exit  daemon')
    parser.add_argument('--nodaemon', default=False, action="store_true",
                        help='dont daemonize')
    parser.add_argument('--notify', default=False, action="store_true",
                        help='dont daemonize')
    args = parser.parse_args()
    if args.notify:
        session_bus = dbus.SessionBus()
        method = session_bus.get_object(
            DBUS_SESSION, DBUS_PATH)\
            .get_dbus_method("activity")
        method(args.notify)
        sys.exit(0)
    elif args.nodaemon:
        main(args)
    else:
        try:
            import daemon
        except ImportError:
            print "pip install daemontools"
        else:
            with daemon.DaemonContext():
                main(args)
