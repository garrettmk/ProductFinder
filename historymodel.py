import logging

from PyQt5.QtSql import *


class ProductHistoryModel(QSqlTableModel):

    def __init__(self, parent = None, asin = ''):
        super(ProductHistoryModel, self).__init__(parent)

        self.fields = ['Timestamp', 'SalesRank', 'Offers', 'Prime', 'Price']
        self.tables = ['Products', 'Observations']
        self.modelReset.connect(self.fetchAll)
        self.modelReset.connect(self.computeStatistics)
        self.setProduct(asin)

    def queryString(self):
        fields = ', '.join(self.fields)
        base = "SELECT {fields} FROM {table} WHERE Asin='{asin}'"
        return ' UNION '.join([base.format(fields=fields, table=table, asin=self.productId) for table in self.tables])

    def setProduct(self, asin):
        """Populate the model with the 256 most recent data points for the specified ASIN."""
        self.productId = asin
        q = QSqlQuery(self.queryString() + ' ORDER BY Timestamp DESC')

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

        minsmaxes = ', '.join(['MIN({0}), MAX({0})'.format(field) for field in self.fields])
        q = QSqlQuery('SELECT ' + minsmaxes + ' FROM (' + self.queryString() + ')')
        if q.lastError().type() != QSqlError.NoError:
            print('Query for mins and maxes failed: ' + q.lastError().text())
            return

        q.first()
        record = q.record()

        for field in self.fields:
            self.mins[field] = record.value('MIN({})'.format(field))
            self.maxes[field] = record.value('MAX({})'.format(field))

    def min(self, fieldname):
        return self.mins[fieldname]

    def max(self, fieldname):
        return self.maxes[fieldname]





