from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtSql import *


class ProductsTableModel(QSqlRelationalTableModel):

    def __init__(self, parent=None):
        super(ProductsTableModel, self).__init__(parent)

    def data(self, index, role=Qt.DisplayRole):

        if role == Qt.TextAlignmentRole:
            if index.column() in [self.fieldIndex('CRank'), self.fieldIndex('SalesRank'), self.fieldIndex('Price'),
                                  self.fieldIndex('Offers')]:
                return Qt.AlignRight | Qt.AlignVCenter

        return super(ProductsTableModel, self).data(index, role)