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
        q = QSqlQuery('SELECT Timestamp, SalesRank, Offers, Prime, Price FROM Observations WHERE Asin=\'{}\' UNION '
                      'SELECT Timestamp, SalesRank, Offers, Prime, Price FROM Products WHERE Asin=\'{}\''.format(asin, asin))

        if q.lastError().type() != QSqlError.NoError:
            logging.debug('ProductHistoryModel: Could not select \'{}\' from database. Error message: \'{}\''.format(asin, q.lastError().text()))
            return False

        self.setQuery(q)
        if self.lastError().type() != QSqlError.NoError:
            logging.debug('ProductHistoryModel: Could not set query. Error message: \'{}\''.format(self.lastError().text()))
            return False

        return True

    def computeStatistics(self):

        if self.rowCount() == 0:
            self.mins = dict.fromkeys(self.fields, 0)
            self.maxes = dict.fromkeys(self.fields, 0)

            today = QDateTime.currentDateTimeUtc()
            self.mins['Timestamp'] = today.toMSecsSinceEpoch()
            self.maxes['Timestamp'] = today.toMSecsSinceEpoch()
            return

        points = dict([(field, []) for field in self.fields])

        for row in range(self.rowCount()):
            record = self.record(row)

            for field in self.fields:
                if field == 'Timestamp':
                    points[field].append(QDateTime.fromString(record.value(field), Qt.ISODate).toMSecsSinceEpoch())
                else:
                    points[field].append(record.value(field))

        for field in self.fields:
            self.mins[field] = min(points[field])
            self.maxes[field] = max(points[field])

    def min(self, fieldname):
        return self.mins[fieldname]

    def max(self, fieldname):
        return self.maxes[fieldname]





