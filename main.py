import sys

#reload(sys)
#sys.setdefaultencoding('UTF-8')

from PyQt5.QtWidgets import QApplication

from mainwindow import *



if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.exec_()
    app.exit()