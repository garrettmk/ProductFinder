from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QDialog
from PyQt5.QtSql import *
from categoriesdialog_ui import *
from delegates import *


class CategoriesDialog(QDialog, Ui_categoryDialog):

    def __init__(self, parent, groupsModel, categoriesModel):
        super(CategoriesDialog, self).__init__(parent)
        self.setupUi(self)

        self.groupsModel = groupsModel
        self.categoriesModel = categoriesModel

        self.groupsModel.setEditStrategy(QSqlTableModel.OnManualSubmit)
        self.categoriesModel.setEditStrategy(QSqlTableModel.OnManualSubmit)

        self.groupsTable.setModel(self.groupsModel)
        self.categoriesTable.setModel(self.categoriesModel)
        self.groupsTable.setItemDelegate(QSqlRelationalDelegate(self))
        self.categoriesTable.setItemDelegate(QSqlRelationalDelegate(self))

        numbers = NumberDelegate(self)
        yesno = YesNoComboDelegate(self)

        self.categoriesTable.setItemDelegateForColumn(self.categoriesModel.fieldIndex('MaxRank'), numbers)
        self.categoriesTable.setItemDelegateForColumn(self.categoriesModel.fieldIndex('Restricted'), yesno)

        self.groupsTable.setColumnHidden(0, True)
        self.categoriesTable.setColumnHidden(0, True)

        self.accepted.connect(self.groupsModel.submitAll)
        self.accepted.connect(self.categoriesModel.submitAll)
        self.rejected.connect(self.groupsModel.revertAll)
        self.rejected.connect(self.categoriesModel.revertAll)

        self.addCategoryButton.clicked.connect(self.addCategory)

    @pyqtSlot()
    def open(self):
        self.groupsModel.select()
        self.categoriesModel.select()

        self.groupsTable.resizeColumnsToContents()
        self.categoriesTable.resizeColumnsToContents()

        groupswidth = self.groupsTable.horizontalHeader().length()
        catswidth = self.categoriesTable.horizontalHeader().length()

        self.groupsTable.setFixedWidth(groupswidth)
        #self.categoriesTable.setFixedWidth(catswidth)

        # self.groupsTable.updateGeometry()
        # self.categoriesTable.updateGeometry()
        #
        # self.updateGeometry()

        super(CategoriesDialog, self).open()

    @pyqtSlot()
    def addCategory(self):
        name = self.categoryLine.text()
        if name == '':
            return

        self.categoryLine.clear()

        record = QSqlRecord()
        record.append(QSqlField('CategoryName'))
        record.setValue(0, name)

        self.categoriesModel.insertRecord(-1, record)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.addCategory()
            return

        super(CategoriesDialog, self).keyPressEvent(event)
