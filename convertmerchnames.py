import sys
import re

from PyQt5.QtWidgets import *
from PyQt5.QtSql import *


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Open the database file
    database = QSqlDatabase.addDatabase('QSQLITE')
    database.setDatabaseName('products.db')
    database.open()

    q1 = QSqlQuery("SELECT * FROM Products")
    q2 = QSqlQuery()
    while q1.next():
        record = q1.record()
        if q2.lastError().type() != QSqlError.NoError:
            print(q2.lastError().text())

        name = record.value('Merchant')
        name = re.sub(r"'", "\'\'", name)
        asin = record.value('Asin')

        # Add the merchant name if it isn't there already
        q2.exec_("INSERT OR IGNORE INTO Merchants(MerchantName) VALUES('{}')".format(name))
        if q2.lastError().type() != QSqlError.NoError:
            print(q2.lastError().text())

        q2.exec_("SELECT MerchantId FROM Merchants WHERE MerchantName='{}'".format(name))
        if q2.lastError().type() != QSqlError.NoError:
            print(q2.lastError().text())

        q2.first()

        merchId = q2.value(0)

        q2.exec_("UPDATE Products SET MerchantId = {} WHERE Asin = '{}'".format(merchId, asin))
        if q2.lastError().type() != QSqlError.NoError:
            print(q2.lastError().text())

    app.exit()