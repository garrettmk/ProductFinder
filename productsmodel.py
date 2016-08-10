from PyQt5.QtCore import *
from PyQt5.QtSql import *

class AmazonProductModel(QSqlRelationalTableModel):

    def __init__(self, parent=None):
        super(AmazonProductModel, self).__init__(parent)

    def data(self, index, role=Qt.DisplayRole):

        if role == Qt.TextAlignmentRole:
            rightaligned = [self.fieldIndex(col) for col in ['CRank', 'SalesRank', 'Price', 'Offers', 'MyPrice',
                                                             'MyCost', 'FBAFees', 'MonthlyVolume', 'Weight',
                                                             'ItemLength', 'ItemWidth', 'ItemHeight']]

            midaligned = [self.fieldIndex(col) for col in ['Watched']]

            if index.column() in rightaligned:
                return Qt.AlignRight | Qt.AlignVCenter
            if index.column() in midaligned:
                return Qt.AlignCenter | Qt.AlignVCenter


class ProductsTableModel(QSqlRelationalTableModel):

    def __init__(self, parent=None):
        super(ProductsTableModel, self).__init__(parent)

        self.setTable('Products')
        self.setEditStrategy(QSqlTableModel.OnRowChange)

        # Set up relations
        self.setRelation(self.fieldIndex('CategoryId'), QSqlRelation('Categories', 'CategoryId', 'CategoryName'))
        self.setRelation(self.fieldIndex('ProductGroupId'), QSqlRelation('ProductGroups', 'ProductGroupId', 'ProductGroupName'))

        # Populate the model
        self.select()

    def data(self, index, role=Qt.DisplayRole):

        if role == Qt.TextAlignmentRole:
            if index.column() in [self.fieldIndex('CRank'), self.fieldIndex('SalesRank'), self.fieldIndex('Price'),
                                  self.fieldIndex('Offers')]:
                return Qt.AlignRight | Qt.AlignVCenter

        return super(ProductsTableModel, self).data(index, role)