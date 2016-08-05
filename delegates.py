from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


class CurrencyDelegate(QStyledItemDelegate):

    def __init__(self, parent=None):
        super(CurrencyDelegate, self).__init__(parent)

    def displayText(self, value, locale):
        return '${:,.2f}'.format(float(value))


class NumberDelegate(QStyledItemDelegate):

    def __init(self, parent=None):
        super(NumberDelegate, self).__init__(parent)

    def displayText(self, value, locale):
        value = str(value)
        value = value.translate({ord(c): None for c in '$#,'})
        return '{:,}'.format(int(value)) if value.isdigit() else ':-('


class PercentDelegate(QStyledItemDelegate):

    def __init__(self, parent=None):
        super(PercentDelegate, self).__init__(parent)

    def displayText(self, value, locale):
        value = str(value)
        value = value.translate({ord(c): None for c in '$#,'})
        return '{:,.2f}%'.format(float(value)) if value.isdigit() else ':-('


class YesNoComboDelegate(QStyledItemDelegate):

    def __init__(self, parent=None):
        super(YesNoComboDelegate, self).__init__(parent)

    def displayText(self, value, locale):
        return 'Yes' if bool(value) else 'No'

    def createEditor(self, parent, options, index):
        box = QComboBox(parent)
        box.addItem('No')
        box.addItem('Yes')
        return box

    def setEditorData(self, editor, index):
        data = str(index.data(Qt.EditRole))
        if data.isdigit():
            editor.setCurrentIndex(int(data))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentIndex(), Qt.EditRole)


class TimestampToLocalDelegate(QStyledItemDelegate):

    def __init__(self, parent=None):
        super(TimestampToLocalDelegate, self).__init__(parent)

    def displayText(self, value, locale):
        utc = QDateTime.fromString(value, Qt.ISODate)
        utc.setTimeSpec(Qt.UTC)

        return utc.toLocalTime().toString('MM-dd-yy hh:mm:ss')

