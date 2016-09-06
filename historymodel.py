import logging

from PyQt5.QtSql import *


class ProductHistoryModel(QSqlRelationalTableModel):

    def __init__(self, parent = None, asin = ''):
        super(ProductHistoryModel, self).__init__(parent)
        self.modelReset.connect(self.fetchAll)
        self.setProduct(asin)

    def setProduct(self, asin):
        """Populate the model with the history data of the specified ASIN."""
        self.productId = asin

        fields = 'Timestamp, SalesRank, Offers, Prime, Price, Merchants.MerchantName'
        join = 'LEFT OUTER JOIN Merchants ON {}.MerchantId = Merchants.MerchantId'

        query = 'SELECT ' + fields + ' FROM ' + ' Products ' + join.format('Products') + ' WHERE Asin=\'{}\''.format(asin)
        query += ' UNION '
        query += 'SELECT ' + fields + ' FROM ' + ' Observations ' + join.format('Observations') + ' WHERE Asin=\'{}\''.format(asin)
        query += ' ORDER BY Timestamp DESC'

        q = QSqlQuery(query)

        if q.lastError().type() != QSqlError.NoError:
            logging.debug('ProductHistoryModel: Could not select \'{}\' from database. Error message: \'{}\''.format(asin, q.lastError().text()))
            return False

        self.setQuery(q)
        if self.lastError().type() != QSqlError.NoError:
            logging.debug('ProductHistoryModel: Could not set query. Error message: \'{}\''.format(self.lastError().text()))
            return False

        return True

    def fetchAll(self):
        while self.canFetchMore():
            self.fetchMore()



