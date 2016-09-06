import webbrowser
import requests
import json

from PyQt5.QtChart import *
from PyQt5.QtGui import *

from mainwindow_ui import *
from categoriesdialog import *
from productsmodel import ProductsTableModel
from historymodel import ProductHistoryModel
from historychart import ProductHistoryChart
from delegates import *
from searchamazon import AmazonSearchEngine, ListingData
from initdb import *


class MainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        # Load up the config data
        with open('config.json') as configfile:
            self.config = json.load(configfile)

        # Set up the update timers
        self.trackingLevels = {int(k):int(v) for k,v in self.config['tracking'].items()}

        # Initialize the various components
        self.initDatabase()
        self.initAmazonSearchEngine()
        self.initProductsModelView()
        self.initDataWidgetMapper()
        self.initHistoryModelView()
        self.initHistoryChart()
        self.initCategoriesDialog()

        # Set up UI connections
        self.keywordsLine.returnPressed.connect(self.newSearch)
        self.searchButton.clicked.connect(self.newSearch)
        self.cancelSearchButton.clicked.connect(self.amazon.stop)
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
        self.actionShow_Table.triggered.connect(self.showHistoryTable)
        self.actionShow_Graph.triggered.connect(self.showHistoryGraph)

        # Initialize the view
        self.productsTable.selectRow(0)
        self.showHistoryGraph()


        # Set up the tracking timers
        self.trackingTimers = {}
        now = QDateTime.currentDateTimeUtc().toTime_t()

        for level in filter(self.trackingLevels.get, self.trackingLevels):
            self.trackingTimers[level] = QTimer(self)
            q = QSqlQuery('SELECT Timestamp FROM Products WHERE Tracking = {} ORDER BY Timestamp ASC LIMIT 1'.format(level))
            q.first()
            if q.isValid():
                timestamp = q.value(0)
                nexttime = (timestamp + self.trackingLevels[level] - now) * 1000
            else:
                nexttime = self.trackingLevels[level] * 1000

            self.trackingTimers[level].timeout.connect(self.updateTrackedProducts)
            self.trackingTimers[level].start(nexttime if nexttime > 0 else 1)


    def initDatabase(self):
        # Check that the SQLite drive is available
        if not QSqlDatabase.isDriverAvailable('QSQLITE'):
            msg = 'SQLite driver not available'
            logging.critical(msg)
            QMessageBox.critical(self, 'Database Error', msg)
            return False

        # Open the database
        self.database = QSqlDatabase.addDatabase('QSQLITE')
        self.database.setDatabaseName('products.db')
        if not self.database.open():
            msg = 'Database could not be opened: ' + self.database.lastError().text()
            logging.critical(msg)
            QMessageBox.critical(self, 'Database Error', msg)
            return False

        # Initialize the tables and triggers
        err = setupDatabaseTables()
        if err.type() != QSqlError.NoError:
            msg = 'Unable to initialize database: ' + err.text()
            logging.critical(msg)
            QMessageBox.critical(self, 'Database error', msg)
            return False

        return True

    def initAmazonSearchEngine(self):
        self.amazon = AmazonSearchEngine(config=self.config['amz'])
        self.amazon.message.connect(self.statusMessage)

        self.lastSearchTime = QDateTime.currentDateTimeUtc().toTime_t()

    def initProductsModelView(self):
        # Initialize the model
        self.productsModel = ProductsTableModel(self)
        self.productsModel.setEditStrategy(QSqlTableModel.OnFieldChange)

        # Make connections
        self.amazon.listingReady.connect(self.productsModel.update)

        # Set up the table view
        self.productsTable.setModel(self.productsModel)
        self.productsTable.setItemDelegate(QSqlRelationalDelegate(self))
        self.productsTable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.productsTable.setSortingEnabled(True)
        self.productsTable.horizontalHeader().setSectionsMovable(True)
        self.productsTable.sortByColumn(self.productsModel.fieldIndex('CRank'), Qt.AscendingOrder)
        self.productsTable.resizeColumnsToContents()

        # Install delegates
        numbers = NumberDelegate(self)
        currency = CurrencyDelegate(self)
        yesno = YesNoComboDelegate(self)
        tolocaltime = TimestampToLocalDelegate(self)
        levels = TrackingLevelDelegate(self)
        levels.setLevels(len(self.trackingLevels))

        for column in map(self.productsModel.fieldIndex, ['CRank', 'SalesRank', 'Offers']):
            self.productsTable.setItemDelegateForColumn(column, numbers)

        for column in [self.productsModel.fieldIndex('Price')]:
            self.productsTable.setItemDelegateForColumn(column, currency)

        for column in map(self.productsModel.fieldIndex, ['Prime', 'PrivateLabel']):
            self.productsTable.setItemDelegateForColumn(column, yesno)

        self.productsTable.setItemDelegateForColumn(self.productsModel.fieldIndex('Tracking'), levels)
        self.productsTable.setItemDelegateForColumn(self.productsModel.fieldIndex('Timestamp'), tolocaltime)

        # Hide some detail columns
        hiddencolumns = map(self.productsModel.fieldIndex, ['Asin', 'ProductGroupName', 'Url', 'PrivateLabel',
                                                            'Manufacturer', 'PartNumber', 'MyPrice', 'MyCost',
                                                            'FBAFees', 'MonthlyVolume', 'Weight', 'ItemWidth',
                                                            'ItemLength', 'ItemHeight', 'UPC'])
        for column in hiddencolumns:
            self.productsTable.horizontalHeader().setSectionHidden(column, True)

    def initHistoryModelView(self):
        # Initialize the model
        self.historyModel = ProductHistoryModel(self)

        # Set up the table view
        self.historyTable.setModel(self.historyModel)
        self.historyTable.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Install delegates
        self.historyTable.setItemDelegate(QSqlRelationalDelegate(self))

        numbers = NumberDelegate(self)
        currency = CurrencyDelegate(self)
        yesno = YesNoComboDelegate(self)
        tolocaltime = TimestampToLocalDelegate(self)

        for column in map(self.historyModel.fieldIndex, ['SalesRank', 'Offers']):
            self.historyTable.setItemDelegateForColumn(column, numbers)

        self.historyTable.setItemDelegateForColumn(self.historyModel.fieldIndex('Price'), currency)
        self.historyTable.setItemDelegateForColumn(self.historyModel.fieldIndex('Prime'), yesno)
        self.historyTable.setItemDelegateForColumn(self.historyModel.fieldIndex('Timestamp'), tolocaltime)

        # Make connections
        self.productsTable.selectionModel().currentRowChanged.connect(self.updateHistoryView)
        self.historyTable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.historyTable.customContextMenuRequested.connect(self.chooseHistoryViewMenu)
        self.historyModel.modelReset.connect(self.historyTable.resizeColumnsToContents)

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
        detailModel = ProductsTableModel(self)
        self.mapper.setModel(detailModel)
        self.mapper.setItemDelegate(QSqlRelationalDelegate(self))
        self.mapper.setSubmitPolicy(QDataWidgetMapper.AutoSubmit)
        self.productsTable.selectionModel().currentRowChanged.connect(self.updateDetailModel)

        catindex = detailModel.fieldIndex('CategoryName')
        catmodel = detailModel.relationModel(catindex)
        self.prodCategoryBox.setModel(catmodel)
        self.prodCategoryBox.setModelColumn(catmodel.fieldIndex('CategoryName'))
        self.prodCategoryBox.currentIndexChanged.connect(self.mapper.submit)

        self.mapper.addMapping(self.prodTitleLine, detailModel.fieldIndex('Title'))
        self.mapper.addMapping(self.prodUrlLine, detailModel.fieldIndex('Url'))
        self.mapper.addMapping(self.prodASINLine, detailModel.fieldIndex('Asin'))
        self.mapper.addMapping(self.prodGroupLine, detailModel.fieldIndex('ProductGroupName'))
        self.mapper.addMapping(self.prodCategoryBox, catindex)
        self.mapper.addMapping(self.prodSalesRankLine, detailModel.fieldIndex('SalesRank'))
        self.mapper.addMapping(self.prodPriceBox, detailModel.fieldIndex('Price'))
        self.mapper.addMapping(self.prodOffersBox, detailModel.fieldIndex('Offers'))
        self.mapper.addMapping(self.prodManufacturerLine, detailModel.fieldIndex('Manufacturer'))
        self.mapper.addMapping(self.prodMpnLine, detailModel.fieldIndex('PartNumber'))
        self.mapper.addMapping(self.prodUPCLine, detailModel.fieldIndex('UPC'))

        self.mapper.addMapping(self.myPriceBox, detailModel.fieldIndex('MyPrice'))
        self.mapper.addMapping(self.myCostBox, detailModel.fieldIndex('MyCost'))
        self.mapper.addMapping(self.fbaFeesBox, detailModel.fieldIndex('FBAFees'))
        self.mapper.addMapping(self.monthlyVolumeBox, detailModel.fieldIndex('MonthlyVolume'))

        self.myPriceBox.valueChanged.connect(self.calculateProfits)
        self.myCostBox.valueChanged.connect(self.calculateProfits)
        self.fbaFeesBox.valueChanged.connect(self.calculateProfits)
        self.monthlyVolumeBox.valueChanged.connect(self.calculateProfits)

    def initHistoryChart(self):
        # Get rid of the placeholder put there by Qt Designer
        self.historyStack.removeWidget(self.historyStack.widget(1))

        self.historyChartView = QChartView(self)
        self.historyStack.addWidget(self.historyChartView)

        self.historyChartView.setRenderHint(QPainter.Antialiasing)
        self.historyChartView.setContextMenuPolicy(Qt.CustomContextMenu)

        self.historyChart = ProductHistoryChart()
        self.historyChart.setModel(self.historyModel)
        self.historyChartView.setChart(self.historyChart)

        self.historyChartView.customContextMenuRequested.connect(self.chooseHistoryViewMenu)

    @pyqtSlot(QModelIndex, QModelIndex)
    def updateDetailModel(self, current, previous):
        asin = self.productsModel.data(self.productsModel.index(current.row(), self.productsModel.fieldIndex('Asin')), Qt.DisplayRole)
        self.mapper.model().setFilter("Asin='{}'".format(asin))
        self.mapper.model().select()
        self.mapper.toFirst()

    @pyqtSlot(QPoint)
    def chooseHistoryViewMenu(self, point):
        menu = QMenu(self)
        menu.addAction(self.actionShow_Graph)
        menu.addAction(self.actionShow_Table)

        if self.historyTable.hasFocus():
            point = self.historyTable.viewport().mapToGlobal(point)
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

        self.mapper.submit()

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
            self.statusMessage('Error pulling from fbatoolkit: ' + response.reason)
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
                self.statusMessage('Error parsing data from fbatoolkit.')
                return

            self.monthlyVolumeBox.setValue(volume)
            self.mapper.submit()
        else:
            self.statusMessage('Error parsing response: data unavailable')

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
    def updateTrackedProducts(self):
        level = 0
        timer = self.sender()

        for key, value in self.trackingTimers.items():
            if value is timer:
                level = key

        if not level:
            print('Could not determine tracking level to update.')
            return

        asins = []
        q = QSqlQuery('SELECT Asin FROM Products WHERE Tracking = {} ORDER BY Timestamp ASC'.format(level))
        while q.next():
            asins.append(q.value(0))

        # Finally - do the updates
        if asins:
            self.amazon.lookup(asins)

        timer.setInterval(self.trackingLevels[level] * 1000)

    @pyqtSlot()
    def applyFilters(self):
        conditions = []

        if self.filterDateBox.currentIndex() == 0:      # All results
            pass
        elif self.filterDateBox.currentIndex() == 1:    # Last search only
            conditions.append("Timestamp >= {}".format(self.lastSearchTime))
        elif self.filterDateBox.currentIndex() == 2:    # Today only
            conditions.append("DATE(Timestamp)=DATE('now')")
        elif self.filterDateBox.currentIndex() == 3:    # Tracked products only
            conditions.append('Tracking > 0')

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
    def newSearch(self):
        keywords = self.keywordsLine.text()
        searchindexes = [x.text() for x in self.searchIndexList.selectedItems()]
        minprice = self.minPriceSearchBox.value()
        maxprice = self.maxPriceSearchBox.value()

        if not keywords or not searchindexes:
            return

        # Note the time this search was started. Used for filtering.
        self.lastSearchTime = QDateTime.currentDateTimeUtc().toTime_t()
        self.amazon.search(keywords, searchindexes, minprice, maxprice)

    @pyqtSlot(str)
    def statusMessage(self, message):
        self.searchStatusList.addItem(message)
        self.searchStatusList.scrollToBottom()

    def updateHistoryView(self, index=QModelIndex()):
        asin = self.prodASINLine.text()

        self.historyModel.setProduct(asin)
