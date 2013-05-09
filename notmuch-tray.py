import sys
import os
import logging
import signal
import argparse
import ConfigParser
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import pyqtRemoveInputHook, QThread
from subprocess import Popen, PIPE, STDOUT

class BaseTrayIcon(QtGui.QSystemTrayIcon):
    def createIcon(self, iconFileName, text, text_color, background_color=None,
                   defaultFontSize=9):
        icon = QtGui.QPixmap(16, 16)
        icon.fill(QtGui.QColor(background_color)
                  if background_color else QtCore.Qt.transparent)
        # Create a painter to paint on to the icon
        # and draw on the text
        painter = QtGui.QPainter(icon)
        #painter.setOpacity(0.5)
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
    textColor = "#FF0004"
    blink=True
    unread=0
    queries={}
    def __init__(self, config, parent=None):
        icon = self.createIcon('', '10', self.textColor, 7)
        QtGui.QSystemTrayIcon.__init__(self, icon, parent)
        self.menu = QtGui.QMenu(parent)
        exitAction = self.menu.addAction("Exit")
        self.setContextMenu(self.menu)
        self.connect(exitAction, QtCore.SIGNAL('triggered()'), self.exit)
        self.init_timer()
        self.config = config
        for query in config.options('queries'):
            self.queries[query] = config.get('queries', query)

    def exit(self):
        sys.exit(0)

    def init_timer(self):
        self.timer = QtCore.QTimer(self)
        self.blink_timer = QtCore.QTimer(self)
        QtCore.QObject.connect(
            self.timer, QtCore.SIGNAL("timeout()"), self.timer_timeout)
        QtCore.QObject.connect(
            self.blink_timer, QtCore.SIGNAL("timeout()"),
            self.blink_timer_timeout)
        self.timer.start(1000)
        self.blink_timer.start(300)
        self.timer_count = 0
        self.timer_count_limit = 10
        self.timer_timeout()

    def blink_timer_timeout(self):
        if self.blink:
            self.setIcon(self.createIcon('', self.unread, self.textColor,
                                         background_color='black'))
        elif self.unread: 
            self.setIcon(self.createIcon('', self.unread, 'black',
                                         background_color='red'))
        self.blink = not self.blink

    def timer_timeout(self):
        mailboxes = []
        for name, query in self.queries.iteritems():
            if name == 'default':
                self.unread = self.get_mail_unread(query.split())
            mailboxes.append(
                "%s: %s "
                % (name, self.get_mail_unread(query.split())))
        message = """
            <h1>Unread Mail</h1>
            Inbox: %s <br>
            %s
        """ % (self.unread,"<br>".join(mailboxes))
        self.setToolTip(message)
        #self.showMessage("New email in ", message, msecs=10000)

    def get_mail_unread(self, query):
        text = None
        try:
            text = Popen(
                ["notmuch", "count"] + query , stdout=PIPE).communicate()[0]
            return int(text)
        except Exception as e:
            return -1

class NotmuchTray(QtGui.QApplication):
    def __init__(self, argv, config):
        super(NotmuchTray, self).__init__(argv)
        self.setQuitOnLastWindowClosed(False)
        self.widget = QtGui.QWidget()
        self.mailIcon = MailTrayIcon(config, self.widget)

    def start(self):
        self.mailIcon.show()

def main(args):
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    config = ConfigParser.RawConfigParser()
    home = os.getenv('USERPROFILE') or os.getenv('HOME')
    config.read(os.path.join(home, '.notmuch-tray.cfg'))

    app = NotmuchTray(sys.argv, config)
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
    args = parser.parse_args()
    if args.nodaemon:
        main(args)
    else:
        try:
            import daemon
        except ImportError:
            print "pip install daemontools" 
        else:
            with daemon.DaemonContext():
                main(args)
