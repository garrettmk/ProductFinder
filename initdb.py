from PyQt5.QtSql import *

#amazonCategories = ['Unknown', 'Beauty', 'Arts, Crafts & Sewing', 'Baby Products', 'Personal Computers', 'Electronics',
#                    'Home & Kitchen', 'Home & Garden', 'Industrial & Scientific', 'Musical Instruments',
#                    'Office Products', 'Patio, Lawn & Garden', 'Pet Supplies', 'Sports & Outdoors',
#                    'Home Improvements', 'Toys & Games', 'Cell Phones & Accessories']
amazonCategories = ['Unknown']

def initDatabase():

    # Create the tables
    q = QSqlQuery()
    if not q.exec_('CREATE TABLE IF NOT EXISTS Products('
                   'Watched BOOL DEFAULT 0, '
                   'CRank INT, '
                   'Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, '
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
                   'ItemHeight FLOAT DEFAULT 0)'):
        return q.lastError()

    if not q.exec_('CREATE TABLE IF NOT EXISTS Categories('
                   'CategoryId INTEGER PRIMARY KEY, '
                   'CategoryName VARCHAR UNIQUE, '
                   'MaxRank INT DEFAULT 0, '
                   'Restricted BOOL, '
                   'FtkToken VARCHAR)'):
        return q.lastError()

    if not q.exec_('CREATE TABLE IF NOT EXISTS ProductGroups('
                   'ProductGroupId INTEGER PRIMARY KEY, '
                   'ProductGroupName VARCHAR UNIQUE, '
                   'CategoryId INT DEFAULT 1)'):
        return q.lastError()

    if not q.exec_('CREATE TABLE IF NOT EXISTS Observations('
                   'Asin VARCHAR, '
                   'Timestamp DATETIME, '
                   'SalesRank INT, '
                   'Offers INT, '
                   'Prime BOOL, '
                   'Price FLOAT, '
                   'FOREIGN KEY(Asin) REFERENCES Products(Asin) ON DELETE CASCADE)'):
        return q.lastError()

    # Populate the categories table
    q.prepare('INSERT OR IGNORE INTO Categories(CategoryName) VALUES(?)')
    for cat in amazonCategories:
        q.addBindValue(cat)
        if not q.exec_():
            return q.lastError()

    # Create a trigger to update a product's category when it's product group association is changed
    q.exec_('DROP TRIGGER IF EXISTS Update_Categories')
    q.exec_('CREATE TRIGGER Update_Categories AFTER UPDATE ON ProductGroups '
            'BEGIN '
            'UPDATE Products SET CategoryId=NEW.CategoryId WHERE ProductGroupId=OLD.ProductGroupId; '
            'END')
    if q.lastError().type() != QSqlError.NoError:
        print('Could not create trigger: ' + q.lastError().text())

    return QSqlError()