import datetime
import webbrowser
import requests

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtChart import *
from PyQt5.QtGui import *

from fuzzywuzzy import fuzz
from mainwindow_ui import *
from categoriesdialog import *
from productsmodel import ProductsTableModel
from delegates import *
from searchamazon import SearchAmazon, ListingData
from initdb import *


class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        # Check that the SQLite drive is available
        if not QSqlDatabase.isDriverAvailable('QSQLITE'):
            QMessageBox.critical(self, 'Database Error', 'SQLite driver not found.')
            return

        # Open the database
        self.database = QSqlDatabase.addDatabase('QSQLITE')
        self.database.setDatabaseName('products.db')
        if not self.database.open():
            QMessageBox.critical(self, 'Database Error',
                                 'Database could not be opened: ' + self.database.lastError().text())
            return

        # Initialize the tables and triggers
        err = initDatabase()
        if err.type() != QSqlError.NoError:
            QMessageBox.critical(self, 'Database error', 'Unable to initialize database: ' + err.text())

        # Set up the SearchAmazon helper
        self.searchThread = QThread()
        self.amazon = SearchAmazon()
        self.amazon.moveToThread(self.searchThread)

        self.amazon.newResultReady.connect(self.processSearchResult)
        self.amazon.searchMessage.connect(self.searchStatusList.addItem)

        self.searchThread.start()

        self.lastSearchTime = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        # Set up the models and views
        self.initProductsModelView()
        self.initObsModelView()
        self.initCategoriesDialog()
        self.initDataWidgetMapper()
        self.initHistoryChart()

        # Set up UI connections
        self.keywordsLine.returnPressed.connect(self.queueNewSearch)
        self.searchButton.clicked.connect(self.queueNewSearch)
        self.cancelSearchButton.clicked.connect(self.amazon.stopSearch)
        self.clearSearchStatusBtn.clicked.connect(self.searchStatusList.clear)

        self.applyFiltersButton.clicked.connect(self.applyFilters)
        self.revertFiltersButton.clicked.connect(self.revertFilters)
        self.updateButton.clicked.connect(self.updateProductInfo)
        self.openAmazonButton.clicked.connect(self.openAmazon)
        self.getFBAFeesButton.clicked.connect(self.getFBAFees)
        self.getVolumeButton.clicked.connect(self.getFTKSalesVolume)
        self.openGoogleButton.clicked.connect(self.openGoogle)
        self.openCamelButton.clicked.connect(self.openCamelCamelCamel)
        self.upcLookupButton.clicked.connect(self.openUPCLookup)

        self.actionEdit_Categories.triggered.connect(self.editProductGroups)
        self.actionUpdate_Watched.triggered.connect(self.updateWatched)
        self.actionRecalculate_Rankings.triggered.connect(self.recalculateRankings)
        self.actionShow_Table.triggered.connect(self.showHistoryTable)
        self.actionShow_Graph.triggered.connect(self.showHistoryGraph)

        # Initialize the view
        self.tableView.selectRow(0)
        self.showHistoryGraph()

        self.startTimer(3600000, Qt.CoarseTimer)


    def initProductsModelView(self):
        # Initialize the model
        self.productsModel = ProductsTableModel(self)
        self.productsModel.setEditStrategy(QSqlTableModel.OnFieldChange)
        self.productsModel.setTable('Products')

        # Set up relations
        self.productsModel.setRelation(self.productsModel.fieldIndex('CategoryId'),
                                       QSqlRelation('Categories', 'CategoryId', 'CategoryName'))
        self.productsModel.setRelation(self.productsModel.fieldIndex('ProductGroupId'),
                                       QSqlRelation('ProductGroups', 'ProductGroupId', 'ProductGroupName'))

        # Populate the model
        self.productsModel.select()

        # Set up the table view
        self.tableView.setModel(self.productsModel)
        self.tableView.setItemDelegate(QSqlRelationalDelegate(self))
        self.tableView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableView.setSortingEnabled(True)
        self.tableView.resizeColumnsToContents()

        # Install delegates
        numbers = NumberDelegate(self)
        currency = CurrencyDelegate(self)
        yesno = YesNoComboDelegate(self)
        tolocaltime = TimestampToLocalDelegate(self)

        for column in map(self.productsModel.fieldIndex, ['CRank', 'SalesRank', 'Offers']):
            self.tableView.setItemDelegateForColumn(column, numbers)

        for column in [self.productsModel.fieldIndex('Price')]:
            self.tableView.setItemDelegateForColumn(column, currency)

        for column in map(self.productsModel.fieldIndex, ['Watched', 'Prime', 'PrivateLabel']):
            self.tableView.setItemDelegateForColumn(column, yesno)

        self.tableView.setItemDelegateForColumn(self.productsModel.fieldIndex('Timestamp'), tolocaltime)

        # Hide some detail columns
        hiddencolumns = map(self.productsModel.fieldIndex, ['Asin', 'ProductGroupName', 'Url', 'PrivateLabel',
                                                            'Manufacturer', 'PartNumber', 'MyPrice', 'MyCost',
                                                            'FBAFees', 'MonthlyVolume', 'Weight', 'ItemWidth',
                                                            'ItemLength', 'ItemHeight', 'UPC'])
        for column in hiddencolumns:
            self.tableView.horizontalHeader().setSectionHidden(column, True)

        # Set sections to be movable, and set the default sorting
        self.tableView.horizontalHeader().setSectionsMovable(True)
        self.tableView.sortByColumn(self.productsModel.fieldIndex('CRank'), Qt.AscendingOrder)


    def initObsModelView(self):
        # Initialize the model
        self.obsModel = QSqlRelationalTableModel(self)
        self.obsModel.setTable('Observations')
        self.obsModel.select()

        # Set up the table view
        self.obsTable.setModel(self.obsModel)
        self.obsTable.horizontalHeader().setSectionHidden(self.obsModel.fieldIndex('Asin'), True)
        self.obsTable.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Install delegates
        self.obsTable.setItemDelegate(QSqlRelationalDelegate(self))

        numbers = NumberDelegate(self)
        currency = CurrencyDelegate(self)
        yesno = YesNoComboDelegate(self)
        tolocaltime = TimestampToLocalDelegate(self)

        for column in map(self.obsModel.fieldIndex, ['SalesRank', 'Offers']):
            self.obsTable.setItemDelegateForColumn(column, numbers)

        self.obsTable.setItemDelegateForColumn(self.obsModel.fieldIndex('Price'), currency)
        self.obsTable.setItemDelegateForColumn(self.obsModel.fieldIndex('Prime'), yesno)
        self.obsTable.setItemDelegateForColumn(self.obsModel.fieldIndex('Timestamp'), tolocaltime)

        # Make connections
        self.tableView.selectionModel().currentRowChanged.connect(self.updateObservations)
        self.obsTable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.obsTable.customContextMenuRequested.connect(self.chooseHistoryViewMenu)


    def initCategoriesDialog(self):
        # Set up the models
        groupsModel = QSqlRelationalTableModel(self)
        groupsModel.setTable('ProductGroups')
        groupsModel.setRelation(groupsModel.fieldIndex('CategoryId'), QSqlRelation('Categories', 'CategoryId', 'CategoryName'))

        categoriesModel = QSqlRelationalTableModel(self)
        categoriesModel.setTable('Categories')

        # Set up the dialog
        self.categoriesDialog = CategoriesDialog(self, groupsModel, categoriesModel)
        self.categoriesDialog.accepted.connect(self.productsModel.select)


    def initDataWidgetMapper(self):
        self.mapper = QDataWidgetMapper(self)
        self.mapper.setModel(self.productsModel)
        self.mapper.setItemDelegate(QSqlRelationalDelegate(self))
        self.mapper.setSubmitPolicy(QDataWidgetMapper.AutoSubmit)
        self.tableView.selectionModel().currentRowChanged.connect(self.mapper.setCurrentModelIndex)

        catindex = self.productsModel.fieldIndex('CategoryName')
        catmodel = self.productsModel.relationModel(catindex)
        self.prodCategoryBox.setModel(catmodel)
        self.prodCategoryBox.setModelColumn(catmodel.fieldIndex('CategoryName'))
        self.prodCategoryBox.currentIndexChanged.connect(self.mapper.submit)

        self.mapper.addMapping(self.prodTitleLine, self.productsModel.fieldIndex('Title'))
        self.mapper.addMapping(self.prodUrlLine, self.productsModel.fieldIndex('Url'))
        self.mapper.addMapping(self.prodASINLine, self.productsModel.fieldIndex('Asin'))
        self.mapper.addMapping(self.prodGroupLine, self.productsModel.fieldIndex('ProductGroupName'))
        self.mapper.addMapping(self.prodCategoryBox, catindex)
        self.mapper.addMapping(self.prodSalesRankLine, self.productsModel.fieldIndex('SalesRank'))
        self.mapper.addMapping(self.prodPriceBox, self.productsModel.fieldIndex('Price'))
        self.mapper.addMapping(self.prodOffersBox, self.productsModel.fieldIndex('Offers'))
        self.mapper.addMapping(self.prodManufacturerLine, self.productsModel.fieldIndex('Manufacturer'))
        self.mapper.addMapping(self.prodMpnLine, self.productsModel.fieldIndex('PartNumber'))
        self.mapper.addMapping(self.prodUPCLine, self.productsModel.fieldIndex('UPC'))

        self.mapper.addMapping(self.myPriceBox, self.productsModel.fieldIndex('MyPrice'))
        self.mapper.addMapping(self.myCostBox, self.productsModel.fieldIndex('MyCost'))
        self.mapper.addMapping(self.fbaFeesBox, self.productsModel.fieldIndex('FBAFees'))
        self.mapper.addMapping(self.monthlyVolumeBox, self.productsModel.fieldIndex('MonthlyVolume'))

        # self.mapper.addMapping(self.prodWeightBox, self.productsModel.fieldIndex('Weight'))
        # self.mapper.addMapping(self.prodLengthBox, self.productsModel.fieldIndex('ItemLength'))
        # self.mapper.addMapping(self.prodWidthBox, self.productsModel.fieldIndex('ItemWidth'))
        # self.mapper.addMapping(self.prodHeightBox, self.productsModel.fieldIndex('ItemHeight'))

        self.myPriceBox.valueChanged.connect(self.calculateProfits)
        self.myCostBox.valueChanged.connect(self.calculateProfits)
        self.fbaFeesBox.valueChanged.connect(self.calculateProfits)
        self.monthlyVolumeBox.valueChanged.connect(self.calculateProfits)

        self.mapper.toFirst()


    def initHistoryChart(self):
        # Get rid of the placeholder put there by Qt Designer
        self.historyStack.removeWidget(self.historyStack.widget(1))

        self.historyChartView = QChartView(self)
        self.historyStack.addWidget(self.historyChartView)

        self.historyChartView.setRenderHint(QPainter.Antialiasing)
        self.historyChartView.setContextMenuPolicy(Qt.CustomContextMenu)

        self.tableView.selectionModel().currentRowChanged.connect(self.updateHistoryChart)
        self.historyChartView.customContextMenuRequested.connect(self.chooseHistoryViewMenu)

    @pyqtSlot(QPoint)
    def chooseHistoryViewMenu(self, point):
        menu = QMenu(self)
        menu.addAction(self.actionShow_Graph)
        menu.addAction(self.actionShow_Table)

        if self.obsTable.hasFocus():
            point = self.obsTable.viewport().mapToGlobal(point)
        elif self.historyChartView.hasFocus():
            point = self.historyChartView.viewport().mapToGlobal(point)

        menu.popup(point)

    @pyqtSlot()
    def showHistoryGraph(self):
        self.actionShow_Graph.setChecked(True)
        self.actionShow_Table.setChecked(False)
        self.historyStack.setCurrentIndex(1)

    @pyqtSlot()
    def showHistoryTable(self):
        self.actionShow_Table.setChecked(True)
        self.actionShow_Graph.setChecked(False)
        self.historyStack.setCurrentIndex(0)

    @pyqtSlot()
    def updateHistoryChart(self):
        asin = self.prodASINLine.text()
        if not asin:
            return

        rankseries = QLineSeries()
        priceseries = QLineSeries()

        moments = []
        ranks = []
        prices = []

        # Get the data from previous observations
        q = QSqlQuery('SELECT Timestamp, SalesRank, Price FROM Observations WHERE Asin=\'{}\' UNION '
                      'SELECT Timestamp, SalesRank, Price FROM Products WHERE Asin=\'{}\''.format(asin, asin))

        while q.next():
            timestamp = QDateTime.fromString(q.value(0), Qt.ISODate)
            timestamp.setTimeSpec(Qt.UTC)

            moments.append(timestamp.toLocalTime().toMSecsSinceEpoch())
            ranks.append(q.value(1))
            prices.append(q.value(2))

            rankseries.append(moments[-1], ranks[-1])
            priceseries.append(moments[-1], prices[-1])

        if len(moments) < 2:
            chart = QChart()
            chart.setTitle('Not enough data')
            self.historyChartView.setChart(chart)
            return

        chart = QChart()

        # Set up the X axis
        axisX = QDateTimeAxis()
        axisX.setFormat('MM/dd')
        axisX.setTitleText('Date')
        chart.legend().hide()
        chart.addAxis(axisX, Qt.AlignBottom)

        # Don't bother with the salesrank graph if they are all zeroes
        if max(ranks) > 0:
            axisL = QValueAxis()
            axisL.setLabelFormat('%i')
            axisL.setTitleText('Sales Rank')
            axisL.setRange(min(ranks), max(ranks)+10)
            chart.addSeries(rankseries)
            chart.addAxis(axisL, Qt.AlignLeft)
            rankseries.attachAxis(axisX)
            rankseries.attachAxis(axisL)
            rankseries.setPointsVisible(True)

        # Set up the right axis (price)
        if max(prices) > 0:
            axisR = QValueAxis()
            axisR.setLabelFormat('$%.2f')
            axisR.setTitleText('Price')
            axisR.setRange(min(prices), max(prices)*1.25)
            chart.addSeries(priceseries)
            chart.addAxis(axisR, Qt.AlignRight)
            priceseries.attachAxis(axisX)
            priceseries.attachAxis(axisR)
            priceseries.setPointsVisible(True)

        self.historyChartView.setChart(chart)


    @pyqtSlot()
    def calculateProfits(self):
        myprice = self.myPriceBox.value()
        mycost = self.myCostBox.value()
        fees = self.fbaFeesBox.value()
        volume = self.monthlyVolumeBox.value()

        profit = myprice - mycost - fees
        margin = 0 if mycost == 0 else profit/mycost

        self.profitEachBox.setValue(profit)
        self.marginBox.setValue(margin * 100)
        self.monthlyCostBox.setValue(mycost * volume)
        self.monthlyProfitBox.setValue(profit * volume)

    @pyqtSlot()
    def recalculateRankings(self):
        self.searchMessage('Recalculating rankings...')

        q = QSqlQuery()
        crankindex = self.productsModel.fieldIndex('CRank')

        for row in range(self.productsModel.rowCount()):
            record = self.productsModel.record(row)

            asin = record.value('Asin')
            salesrank = record.value('SalesRank')
            offers = record.value('Offers')
            prime = record.value('Prime')
            catname = record.value('CategoryName')
            q.exec_("SELECT CategoryId FROM Categories WHERE CategoryName='{}'".format(catname))
            q.first()
            categoryId = q.value(0)

            crank = self.getRanking(categoryId, salesrank, offers, prime)
            self.productsModel.setData(self.productsModel.index(row, crankindex), crank)

        self.searchMessage('Rank calculations complete.')

    @pyqtSlot()
    def getFBAFees(self):
        url = QUrl('https://sellercentral.amazon.com/fba/profitabilitycalculator/index')
        webbrowser.open(url.toString(), new=2, autoraise=True)

    @pyqtSlot()
    def getFTKSalesVolume(self):
        # Get the FtkToken for the given category
        category = self.prodCategoryBox.currentText()
        q = QSqlQuery("SELECT FtkToken FROM Categories WHERE CategoryName='{}'".format(category))
        q.first()
        token = q.value(0)
        if token is None or token == '':
            QMessageBox.warning(self, 'No FBAToolkit Token', 'No FtkToken for category {}'.format(category))
            return

        salesrank = self.prodSalesRankLine.text()

        params = {'category': token, 'rank': salesrank}
        response = requests.get('http://fbatoolkit.com/estimate_ajax', params=params)
        if response.status_code != 200:
            self.searchMessage('Error pulling from fbatoolkit: ' + response.reason)
            return

        data = response.json()
        # The response from FBA Toolkit for 'sales_per_30day_avg' comes as either an integer value,
        # or a string in the form of '1 every 2 days'
        if 'sales_per_day_30day_avg' in data:
            try:
                volume = int(data['sales_per_day_30day_avg']) * 30
            except ValueError:
                nums = [float(s) for s in data['sales_per_day_30day_avg'].split() if s.isdigit()]
                volume = int(nums[0] / nums[1] * 30)
            except:
                self.searchMessage('Error parsing data from fbatoolkit.')
                return

            self.monthlyVolumeBox.setValue(volume)
            #self.mapper.submit()
        else:
            self.searchMessage('Error parsing response: data unavailable')

    def getRanking(self, categoryId, salesrank, offers, prime):
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

    @pyqtSlot()
    def updateProductInfo(self):
        asin = self.prodASINLine.text()
        self.amazon.asinSearch(asin)

    @pyqtSlot()
    def openAmazon(self):
        url = self.prodUrlLine.text()
        webbrowser.open_new_tab(url)

    @pyqtSlot()
    def openGoogle(self):
        mfg = self.prodManufacturerLine.text()
        mpn = self.prodMpnLine.text()

        url = QUrl('http://www.google.com/')
        url.setQuery('q=' + '+'.join([mfg, mpn]))
        webbrowser.open(url.toString(), new=2, autoraise=True)

    @pyqtSlot()
    def openCamelCamelCamel(self):
        asin = self.prodASINLine.text()

        url = QUrl('http://camelcamelcamel.com/search')
        url.setQuery('sq=' + asin)
        webbrowser.open(url.toString(), new=2, autoraise=True)

    @pyqtSlot()
    def openUPCLookup(self):
        if self.prodUPCLine.text().isdigit():
            webbrowser.open('http://www.upcitemdb.com/upc/{}'.format(self.prodUPCLine.text()), new=2, autoraise=True)

    @pyqtSlot()
    def editProductGroups(self):
        self.categoriesDialog.open()

    @pyqtSlot()
    def updateWatched(self):
        q = QSqlQuery('SELECT Asin FROM Products WHERE Watched=1')

        count = 0
        while q.next():
            count += 1
            self.amazon.asinSearch(q.value(0))

    @pyqtSlot()
    def applyFilters(self):
        conditions = []

        if self.filterDateBox.currentIndex() == 0:      # All results
            pass
        elif self.filterDateBox.currentIndex() == 1:    # Last search only
            conditions.append("Timestamp >= '{}' AND Watched=0".format(self.lastSearchTime))
        elif self.filterDateBox.currentIndex() == 2:    # Today only
            conditions.append("DATE(Timestamp)=DATE('now') AND Watched=0")
        elif self.filterDateBox.currentIndex() == 3:    # Watched only
            conditions.append('Watched=1')

        if self.withKeywordsLine.text():
            conditions.append("INSTR(LOWER(Title), LOWER('{}'))".format(self.withKeywordsLine.text()))

        if self.withoutKeywordsLine.text():
            conditions.append("NOT INSTR(LOWER(Title), LOWER('{}'))".format(self.withoutKeywordsLine.text()))

        if self.primeCheck.checkState() == Qt.Unchecked:
            conditions.append('Prime=0')

        if self.amazonCheck.checkState() == Qt.Unchecked:
            conditions.append("NOT INSTR(LOWER(Merchant), 'amazon')")

        if self.privateLabelCheck.checkState() == Qt.Unchecked:
            conditions.append("PrivateLabel=0")

        if self.restrictedCheck.checkState() == Qt.Unchecked:
            conditions.append("CategoryName NOT IN (SELECT CategoryName FROM Categories WHERE Restricted=1)")

        if self.zeroesCheck.checkState() == Qt.Unchecked:
            conditions.append("CRank <> 0")

        if self.offersFilterBox.value() > 0:
            conditions.append("Offers <= {}".format(self.offersFilterBox.value()))

        if self.minPriceFilterBox.value() > 0:
            conditions.append("Price >= {}".format(self.minPriceFilterBox.value()))
        if self.maxPriceFilterBox.value() > 0:
            conditions.append("Price <= {}".format(self.maxPriceFilterBox.value()))

        if self.rankFilterBox.value() > 0:
            conditions.append("CRank <= {}".format(self.rankFilterBox.value()))

        # if self.weightFilterBox.value() > 0:
        #     conditions.append("Weight <= {}".format(self.weightFilterBox.value()))
        #
        # if self.volumeFilterBox.value() > 0:
        #     conditions.append("(ItemLength * ItemWidth * ItemHeight) <= {}".format(self.volumeFilterBox.value()))

        bigfilter = ' AND '.join(conditions)

        self.productsModel.setFilter(bigfilter)
        self.productsModel.select()

    @pyqtSlot()
    def revertFilters(self):

        checkboxes = [self.primeCheck, self.amazonCheck, self.privateLabelCheck, self.restrictedCheck, self.zeroesCheck]
        for box in checkboxes:
            box.setCheckState(Qt.Checked)

        spinboxes = [self.offersFilterBox, self.minPriceFilterBox, self.maxPriceFilterBox, self.rankFilterBox]

        for box in spinboxes:
            box.setValue(0)

        self.withKeywordsLine.clear()
        self.withoutKeywordsLine.clear()

        self.applyFilters()

    @pyqtSlot()
    def queueNewSearch(self):
        keywords = self.keywordsLine.text()
        searchindexes = self.searchIndexList.selectedItems()
        minprice = self.minPriceSearchBox.value()
        maxprice = self.maxPriceSearchBox.value()

        if not keywords or not len(searchindexes):
            return

        # Note the time this search was started. Used for filtering.
        self.lastSearchTime = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        for index in searchindexes:
            self.amazon.keywordSearch(keywords, index.text(), minprice, maxprice)

    @pyqtSlot(str)
    def searchMessage(self, message):
        self.searchStatusList.addItem(message)
        self.searchStatusList.scrollToBottom()

    @pyqtSlot(ListingData)
    def processSearchResult(self, listing):
        q1 = QSqlQuery()
        q2 = QSqlQuery()

        # Add the product group if it isn't there already
        q1.exec_("INSERT OR IGNORE INTO ProductGroups(ProductGroupName) VALUES('{}')".format(listing.productgroup))
        q1.exec_("SELECT ProductGroupId FROM ProductGroups WHERE ProductGroupName='{}'".format(listing.productgroup))
        q1.first()

        productgroupId = q1.value(0)

        # Get the category association
        q1.exec_("SELECT CategoryId FROM ProductGroups WHERE ProductGroupId={}".format(productgroupId))
        q1.first()

        categoryId = q1.value(0)
        watched = False
        myprice = 0
        mycost = 0
        fbafees = 0
        monthlyvolume = 0

        # Check if the listing has already been added to the database
        q1.exec_("SELECT * FROM Products WHERE Asin='{}'".format(listing.asin))
        q1.first()
        if q1.isValid():
            # The listing is already in the database. Add it's current values to the observation table
            q2.prepare("INSERT INTO Observations(Asin, Timestamp, SalesRank, Offers, Prime, Price) "
                       "VALUES(?, ?, ?, ?, ?, ?)")
            q2.addBindValue(q1.value(q1.record().indexOf('Asin')))
            q2.addBindValue(q1.value(q1.record().indexOf('Timestamp')))
            q2.addBindValue(q1.value(q1.record().indexOf('SalesRank')))
            q2.addBindValue(q1.value(q1.record().indexOf('Offers')))
            q2.addBindValue(q1.value(q1.record().indexOf('Prime')))
            q2.addBindValue(q1.value(q1.record().indexOf('Price')))
            q2.exec_()

            # Grab values that we don't want to overwrite
            q1.exec_("SELECT Watched, MyPrice, MyCost, FBAFees, MonthlyVolume FROM Products WHERE Asin='{}'".format(listing.asin))
            q1.first()
            watched = q1.value(0)
            myprice = q1.value(1)
            mycost = q1.value(2)
            fbafees = q1.value(3)
            monthlyvolume = q1.value(4)


        # Calculate the CRank
        crank = self.getRanking(categoryId, listing.salesrank, listing.offers, listing.prime)

        # Determine if it is a private label product
        if (fuzz.partial_ratio(listing.merchant.lower(), listing.title.lower()) > 80) or \
                (fuzz.partial_ratio(listing.merchant.lower(), listing.make.lower()) > 80):
            privatelabel = True
        else:
            privatelabel = False

        q1.prepare('INSERT OR REPLACE INTO Products(Watched, CRank, Asin, ProductGroupId, CategoryId, SalesRank, Offers,'
                   'Prime, Price, Merchant, Title, Url, PrivateLabel, Manufacturer, PartNumber, Weight, ItemLength,'
                   'ItemWidth, ItemHeight, MyPrice, MyCost, FBAFees, MonthlyVolume, UPC) '
                   'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')

        fields = [watched, crank, listing.asin, productgroupId, categoryId, listing.salesrank, listing.offers,
                  listing.prime, listing.price, listing.merchant, listing.title, listing.url, privatelabel,
                  listing.make, listing.model, listing.weight/100, listing.length/100,
                  listing.width/100, listing.height/100, myprice, mycost, fbafees, monthlyvolume, listing.upc]

        for field in fields:
            q1.addBindValue(field)

        q1.exec_()

        if q1.lastError().type() != QSqlError.NoError:
            print('Could not insert record: ' + q1.lastError().text())

        self.productsModel.select()

    def updateObservations(self, index):
        asincol = self.productsModel.fieldIndex('Asin')
        index = self.productsModel.index(index.row(), asincol)
        asin = self.productsModel.data(index, Qt.DisplayRole)

        self.obsModel.setFilter("Asin='{}'".format(asin))
        self.obsModel.select()

    def timerEvent(self, QTimerEvent):
        self.updateWatched()
        print('Update!')