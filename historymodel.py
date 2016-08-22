import logging

from PyQt5.QtCore import *
from PyQt5.QtSql import *


class ProductHistoryModel(QSqlTableModel):

    def __init__(self, asin = '', parent = None):
        super(ProductHistoryModel, self).__init__(parent)

        self.setProduct(asin)

    def setProduct(self, asin):
        q = QSqlQuery('SELECT Timestamp, SalesRank, Offers, Prime, Price FROM Observations WHERE Asin=\'{}\' UNION '
                      'SELECT Timestamp, SalesRank, Offers, Prime, Price FROM Products WHERE Asin=\'{}\''.format(asin, asin))

        if q.lastError().type() != QSqlError.NoError:
            logging.debug('ProductHistoryModel: Could not select \'{}\' from database. Error message: \'{}\''.format(asin, q.lastError().text()))
            return False

        self.setQuery(q)
        if self.lastError() != QSqlError.NoError:
            logging.debug('ProductHistoryModel: Could not set query. Error message: \'{}\''.format(self.lastError().text()))
            return False

        return True
