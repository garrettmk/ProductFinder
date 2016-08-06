from PyQt5.QtCore import *
from PyQt5.QtSql import *


class ProductsTableModel(QSqlRelationalTableModel):

    def __init__(self, parent=None):
        super(ProductsTableModel, self).__init__(parent)

        self.setTable('Products')
        self.setEditStrategy(QSqlTableModel.OnRowChange)

        # Set up relations
        self.setRelation(self.fieldIndex('CategoryId'), QSqlRelation('Categories', 'CategoryId', 'CategoryName'))
        self.setRelation(self.fieldIndex('ProductGroupId'), QSqlRelation('ProductGroups', 'ProductGroupId', 'ProductGroupName'))

        # Populate the model
        self.productsModel.select()

    def data(self, index, role=Qt.DisplayRole):

        if role == Qt.TextAlignmentRole:
            if index.column() in [self.fieldIndex('CRank'), self.fieldIndex('SalesRank'), self.fieldIndex('Price'),
                                  self.fieldIndex('Offers')]:
                return Qt.AlignRight | Qt.AlignVCenter

        return super(ProductsTableModel, self).data(index, role)