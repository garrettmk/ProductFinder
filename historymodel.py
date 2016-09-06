from PyQt5.QtSql import *


class ProductHistoryModel(QSqlTableModel):

    def __init__(self, parent = None, asin = ''):
        super(ProductHistoryModel, self).__init__(parent)
        self.setTable('ProductHistory')
        self.modelReset.connect(self.fetchAll)
        self.setProduct(asin)

    def setProduct(self, asin):
        """Populate the model with the history data of the specified ASIN."""
        self.productId = asin
        self.setFilter('Asin=\'{}\''.format(asin))
        if not self.rowCount():
            self.select()

        if self.lastError().type() != QSqlError.NoError:
            print('ProductHistoryModel: Could not set product.')
            return False

        return True

    def fetchAll(self):
        while self.canFetchMore():
            self.fetchMore()



