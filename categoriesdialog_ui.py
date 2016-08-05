# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'categoriesdialog.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_categoryDialog(object):
    def setupUi(self, categoryDialog):
        categoryDialog.setObjectName("categoryDialog")
        categoryDialog.resize(887, 431)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(categoryDialog.sizePolicy().hasHeightForWidth())
        categoryDialog.setSizePolicy(sizePolicy)
        self.verticalLayout = QtWidgets.QVBoxLayout(categoryDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.categoryLine = QtWidgets.QLineEdit(categoryDialog)
        self.categoryLine.setObjectName("categoryLine")
        self.horizontalLayout.addWidget(self.categoryLine)
        self.addCategoryButton = QtWidgets.QPushButton(categoryDialog)
        self.addCategoryButton.setObjectName("addCategoryButton")
        self.horizontalLayout.addWidget(self.addCategoryButton)
        self.gridLayout.addLayout(self.horizontalLayout, 1, 1, 1, 1)
        self.groupsTable = QtWidgets.QTableView(categoryDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupsTable.sizePolicy().hasHeightForWidth())
        self.groupsTable.setSizePolicy(sizePolicy)
        self.groupsTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.groupsTable.setAlternatingRowColors(True)
        self.groupsTable.setSortingEnabled(True)
        self.groupsTable.setObjectName("groupsTable")
        self.groupsTable.horizontalHeader().setStretchLastSection(True)
        self.gridLayout.addWidget(self.groupsTable, 0, 0, 1, 1)
        self.categoriesTable = QtWidgets.QTableView(categoryDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.categoriesTable.sizePolicy().hasHeightForWidth())
        self.categoriesTable.setSizePolicy(sizePolicy)
        self.categoriesTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.categoriesTable.setAlternatingRowColors(True)
        self.categoriesTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.categoriesTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.categoriesTable.setSortingEnabled(True)
        self.categoriesTable.setObjectName("categoriesTable")
        self.categoriesTable.horizontalHeader().setStretchLastSection(True)
        self.gridLayout.addWidget(self.categoriesTable, 0, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.buttonBox = QtWidgets.QDialogButtonBox(categoryDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(categoryDialog)
        self.buttonBox.accepted.connect(categoryDialog.accept)
        self.buttonBox.rejected.connect(categoryDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(categoryDialog)

    def retranslateUi(self, categoryDialog):
        _translate = QtCore.QCoreApplication.translate
        categoryDialog.setWindowTitle(_translate("categoryDialog", "Product Groups & Category"))
        self.addCategoryButton.setText(_translate("categoryDialog", "Add New"))

