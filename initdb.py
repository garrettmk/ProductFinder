import logging
from PyQt5.QtSql import *


def setupDatabaseTables():
    db = QSqlDatabase.database()
    db.transaction()

    # Create the tables
    q = QSqlQuery()
    q.exec_('CREATE TABLE IF NOT EXISTS Products('
               'Watched BOOL DEFAULT 0, '
               'CRank INT, '
               'Timestamp INT, '
               'Asin VARCHAR PRIMARY KEY, '
               'ProductGroupId INT, '
               'CategoryId INT DEFAULT 1,'
               'SalesRank INT, '
               'Offers INT, '
               'Prime BOOL, '
               'Price FLOAT, '
               'Merchant VARCHAR, '
               'Title VARCHAR, '
               'Url VARCHAR, '
               'PrivateLabel BOOL, '
               'Manufacturer VARCHAR, '
               'PartNumber VARCHAR, '
               'MyPrice FLOAT, '
               'MyCost FLOAT,'
               'FBAFees FLOAT, '
               'MonthlyVolume INT, '
               'Weight FLOAT DEFAULT 0, '
               'ItemLength FLOAT DEFAULT 0, '
               'ItemWidth FLOAT DEFAULT 0, '
               'ItemHeight FLOAT DEFAULT 0)')

    q.exec_('CREATE TABLE IF NOT EXISTS Categories('
               'CategoryId INTEGER PRIMARY KEY, '
               'CategoryName VARCHAR UNIQUE, '
               'MaxRank INT DEFAULT 0, '
               'Restricted BOOL, '
               'FtkToken VARCHAR)')

    q.exec_('CREATE TABLE IF NOT EXISTS ProductGroups('
               'ProductGroupId INTEGER PRIMARY KEY, '
               'ProductGroupName VARCHAR UNIQUE, '
               'CategoryId INT DEFAULT 1)')

    q.exec_('CREATE TABLE IF NOT EXISTS Observations('
               'Asin VARCHAR, '
               'Timestamp INT, '
               'SalesRank INT, '
               'Offers INT, '
               'Prime BOOL, '
               'Price FLOAT, '
               'FOREIGN KEY(Asin) REFERENCES Products(Asin) ON DELETE CASCADE)')

    # Insert a default category
    q.prepare('INSERT OR IGNORE INTO Categories(CategoryName) VALUES("Unknown")')

    # Create a trigger to update a product's category when it's product group association is changed
    q.exec_('DROP TRIGGER IF EXISTS Update_Categories')
    q.exec_('CREATE TRIGGER Update_Categories AFTER UPDATE ON ProductGroups '
            'BEGIN '
            'UPDATE Products SET CategoryId=NEW.CategoryId WHERE ProductGroupId=OLD.ProductGroupId; '
            'END')

    if not db.commit():
        logging.debug('Table setup failed: ' + db.lastError().text())
        db.rollback()
        return db.lastError()

    return QSqlError()
