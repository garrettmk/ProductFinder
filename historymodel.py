import logging

from PyQt5.QtCore import *
from PyQt5.QtSql import *


class ProductHistoryModel(QSqlTableModel):

    def __init__(self, asin = '', parent = None):
        super(ProductHistoryModel, self).__init__(parent)

        self.fields = ['Timestamp', 'SalesRank', 'Offers', 'Prime', 'Price']
        self.computeStatistics()

        self.modelReset.connect(self.computeStatistics)

        self.setProduct(asin)

    def setProduct(self, asin):
        """Populate the model with the 256 most recent data points for the specified ASIN."""
        q = QSqlQuery('SELECT Timestamp, SalesRank, Offers, Prime, Price FROM Products WHERE Asin=\'{}\' UNION '
                      'SELECT Timestamp, SalesRank, Offers, Prime, Price FROM Observations WHERE Asin=\'{}\' '
                      'ORDER BY Timestamp DESC'.format(asin, asin))

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

    def computeStatistics(self):

        if self.rowCount() == 0:
            self.mins = dict.fromkeys(self.fields, 0)
            self.maxes = dict.fromkeys(self.fields, 0)
            return

        points = dict([(field, []) for field in self.fields])

        for row in range(self.rowCount()):
            record = self.record(row)

            for field in self.fields:
                points[field].append(record.value(field))

        for field in self.fields:
            self.mins[field] = min(points[field])
            self.maxes[field] = max(points[field])

    def min(self, fieldname):
        return self.mins[fieldname]

    def max(self, fieldname):
        return self.maxes[fieldname]





