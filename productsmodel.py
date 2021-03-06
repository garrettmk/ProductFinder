import re

from PyQt5.QtCore import *
from PyQt5.QtSql import *

from fuzzywuzzy import fuzz


class ProductsTableModel(QSqlRelationalTableModel):

    def __init__(self, parent=None):
        super(ProductsTableModel, self).__init__(parent)

        self.setTable('Products')
        self.setEditStrategy(QSqlTableModel.OnRowChange)

        # Set up relations
        self.setRelation(self.fieldIndex('CategoryId'), QSqlRelation('Categories', 'CategoryId', 'CategoryName'))
        self.setRelation(self.fieldIndex('ProductGroupId'), QSqlRelation('ProductGroups', 'ProductGroupId', 'ProductGroupName'))
        self.setRelation(self.fieldIndex('MerchantId'), QSqlRelation('Merchants', 'MerchantId', 'MerchantName'))

        # Populate the model
        self.select()

    def data(self, index, role=Qt.DisplayRole):

        if role == Qt.TextAlignmentRole:
            if index.column() in [self.fieldIndex('CRank'), self.fieldIndex('SalesRank'), self.fieldIndex('Price'),
                                  self.fieldIndex('Offers')]:
                return Qt.AlignRight | Qt.AlignVCenter

        return super(ProductsTableModel, self).data(index, role)

    def getListingRank(self, categoryId, salesrank, offers, prime):
        """Return a rank value based on the category, sales rank, number of offers, and Prime availability."""
        q = QSqlQuery("SELECT MaxRank FROM Categories WHERE CategoryId={}".format(categoryId))
        if q.lastError().type() != QSqlError.NoError:
            print("Could not fetch MaxRank from Categories: " + q.lastError().text())

        q.first()
        maxrank = int(q.value(0)) if q.value(0) is not None else 0

        if maxrank > 0:
            crank = salesrank * 100000 / maxrank

            if prime:
                crank *= offers + 1
            else:
                crank *= 1.25 ** offers

            return int(crank)
        else:
            return 0

    def update(self, listing):
        """Insert a listing into the database, or update an existing entry."""
        q = QSqlQuery()

        # Add the product group if it isn't there already
        q.exec_("INSERT OR IGNORE INTO ProductGroups(ProductGroupName) VALUES('{}')".format(listing.productgroup))
        q.exec_("SELECT ProductGroupId FROM ProductGroups WHERE ProductGroupName='{}'".format(listing.productgroup))
        q.first()

        productgroupId = q.value(0)

        # Get the category association
        q.exec_("SELECT CategoryId FROM ProductGroups WHERE ProductGroupId={}".format(productgroupId))
        q.first()

        categoryId = q.value(0)

        # Add the merchant name
        merchname = re.sub(r"'", "\'\'", listing.merchant)                      # SQL uses two single quotes to escape a single quote...
        q.exec_("INSERT OR IGNORE INTO Merchants(MerchantName) VALUES('{}')".format(merchname))
        q.exec_("SELECT MerchantId FROM Merchants WHERE MerchantName='{}'".format(merchname))
        q.first()

        merchantId = q.value(0)

        tracking = 0
        myprice = 0
        mycost = 0
        fbafees = 0
        monthlyvolume = 0

        # Check if the listing has already been added to the database
        q.exec_("SELECT * FROM Products WHERE Asin='{}'".format(listing.asin))
        q.first()
        if q.isValid():
            record = q.record()
            # The listing is already in the database. Add it's current values to the observation table
            q.prepare("INSERT INTO Observations(Asin, Timestamp, SalesRank, Offers, Prime, Price, MerchantId) "
                       "VALUES(?, ?, ?, ?, ?, ?, ?)")
            q.addBindValue(record.value('Asin'))
            q.addBindValue(record.value('Timestamp'))
            q.addBindValue(record.value('SalesRank'))
            q.addBindValue(record.value('Offers'))
            q.addBindValue(record.value('Prime'))
            q.addBindValue(record.value('Price'))
            q.addBindValue(record.value('MerchantId'))
            q.exec_()

            # Grab values that we don't want to overwrite
            q.exec_("SELECT Tracking, MyPrice, MyCost, FBAFees, MonthlyVolume FROM Products WHERE Asin='{}'".format(
                listing.asin))
            q.first()
            tracking = q.value(0)
            myprice = q.value(1)
            mycost = q.value(2)
            fbafees = q.value(3)
            monthlyvolume = q.value(4)

        # Calculate the CRank
        crank = self.getListingRank(categoryId, listing.salesrank, listing.offers, listing.prime)

        # Determine if it is a private label product
        if (fuzz.partial_ratio(listing.merchant.lower(), listing.title.lower()) > 80) or \
                (fuzz.partial_ratio(listing.merchant.lower(), listing.make.lower()) > 80):
            privatelabel = True
        else:
            privatelabel = False

        time = QDateTime.currentDateTimeUtc().toTime_t()

        q.prepare(
            'INSERT OR REPLACE INTO Products(Tracking, CRank, Timestamp, Asin, ProductGroupId, CategoryId, SalesRank, Offers,'
            'Prime, Price, MerchantId, Title, Url, PrivateLabel, Manufacturer, PartNumber, Weight, ItemLength,'
            'ItemWidth, ItemHeight, MyPrice, MyCost, FBAFees, MonthlyVolume, UPC) '
            'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')

        fields = [tracking, crank, time, listing.asin, productgroupId, categoryId, listing.salesrank, listing.offers,
                  listing.prime, listing.price, merchantId, listing.title, listing.url, privatelabel,
                  listing.make, listing.model, listing.weight / 100, listing.length / 100,
                  listing.width / 100, listing.height / 100, myprice, mycost, fbafees, monthlyvolume, listing.upc]

        for field in fields:
            q.addBindValue(field)

        q.exec_()

        if q.lastError().type() != QSqlError.NoError:
            print('Could not insert record: ' + q.lastError().text())

        self.select()
