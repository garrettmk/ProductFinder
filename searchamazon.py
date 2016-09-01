import random
import time
import bottlenose

from lxml import objectify
from urllib.request import HTTPError
from PyQt5.QtCore import *


class ListingData(object):

    def __init__(self):
        self.asin = str()
        self.productgroup = str()
        self.category = str()
        self.salesrank = int()
        self.offers = int()
        self.prime = bool()
        self.price = float()
        self.merchant = str()
        self.title = str()
        self.url = str()

        self.myprice = float()
        self.mycost = float()
        self.fbafees = float()
        self.volume = int()

        self.length = 0
        self.width = 0
        self.height = 0
        self.weight = 0

        self.make = ''
        self.model = ''
        self.upc = 0


class AmzSearchRequest:

    def __init__(self, keywords=None, indexes=[], minprice=None, maxprice=None):
        self.keywords = keywords
        self.searchindexes = indexes
        self.minprice = minprice
        self.maxprice = maxprice


class AmzLookupRequest:

    def __init__(self, asins=[]):
        self.asins = asins


class AmazonSearchEngine(QThread):

    listingReady = pyqtSignal(ListingData)
    finished = pyqtSignal()
    message = pyqtSignal(str)

    def __init__(self, config):
        super(AmazonSearchEngine, self).__init__()

        self.abort = False
        self.retries = 0
        self.scanned = 0
        self.pending = []
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self.responsegroups = 'ItemAttributes,OfferFull,SalesRank,Variations'
        self.bottlenose = bottlenose.Amazon(config['access_key'], config['secret_key'], config['associate_tag'],
                                            Parser=objectify.fromstring, MaxQPS=0.9)

    def search(self, keywords, indexes, minprice=None, maxprice=None):
        """Search for ``keywords`` in each category listed in ``indexes``."""
        self.mutex.lock()
        self.abort = False
        self.pending.append(AmzSearchRequest(keywords, indexes, minprice, maxprice))
        self.mutex.unlock()

        if not self.isRunning():
            self.start(self.LowPriority)
        else:
            self.condition.wakeOne()

    def lookup(self, asins):
        """Look up each ASIN listed in ``asins``."""
        self.mutex.lock()
        self.abort = False
        self.pending.append(AmzLookupRequest(asins))
        self.mutex.unlock()

        if not self.isRunning():
            self.start(self.LowPriority)
        else:
            self.condition.wakeOne()

    def stop(self):
        """Abort any current or pending operations."""
        self.mutex.lock()
        self.abort = True
        self.pending.clear()
        self.mutex.unlock()

    def run(self):
        while True:
            self.mutex.lock()
            if not self.pending:
                self.condition.wait(self.mutex)
            op = self.pending.pop(0)
            self.mutex.unlock()

            if isinstance(op, AmzSearchRequest):
                self.scanned = 0
                self._item_search(op)
                self.message.emit('Search complete. {} listings scanned.'.format(self.scanned))
            elif isinstance(op, AmzLookupRequest):
                self.scanned = 0
                self._item_lookup(op)
                self.message.emit('Lookup complete. {} listings scanned.'.format(self.scanned))

            if not self.pending:
                self.finished.emit()


    def _item_lookup(self, op, parent=None):
        for asin in op.asins:
            if self.abort:
                return

            self.message.emit('Looking up {}...'.format(asin))

            try:
                response = self.bottlenose.ItemLookup(ErrorHandler=self._bottlenose_error_handler, ItemId=asin, ResponseGroup=self.responsegroups)
            except Exception as e:
                self.message.emit(repr(e))
                continue

            if not self._validate(response):
                continue

            self._process(response, parent)

    def _item_search(self, op):
        for index in op.searchindexes:
            if self.abort:
                return

            self.message.emit('Searching for {} in {}...'.format(op.keywords, index))

            options = {}
            if index != 'All' and index != 'Blended':
                if op.minprice:
                    options['MinimumPrice'] = int(op.minprice * 100)
                if op.maxprice:
                    options['MaximumPrice'] = int(op.maxprice * 100)

            maxpages = 5 if index == 'All' else 10

            for page in range(1, maxpages + 1):
                if self.abort:
                    return

                try:
                    response = self.bottlenose.ItemSearch(ErrorHandler=self._bottlenose_error_handler, Keywords=op.keywords,
                                                          SearchIndex=index, ResponseGroup=self.responsegroups, ItemPage=page)
                except Exception as e:
                    self.message.emit(repr(e))
                    continue

                if not self._validate(response):
                    break

                self._process(response)


    def _validate(self, response):
        if response is None:
            return False

        errors = response.xpath('//aws:Error', namespaces={'aws': response.nsmap.get(None)})
        if errors:
            for error in errors:
                self.message.emit(error.Code + ': ' + error.Message)
            return False

        return True

    def _process(self, response, parent=None):
        for item in response.Items.Item:
            if self.abort:
                return

            # Check if this is actually a parent listing. If so, do a sub-search to get the children
            parentASIN = str(getattr(item, 'ParentASIN', None))
            if parentASIN == item.ASIN:
                children = [str(asin) for asin in item.xpath('./aws:Variations/aws:Item/aws:ASIN', namespaces={'aws': item.nsmap.get(None)})]
                self._item_lookup(AmzLookupRequest(children), item)
            else:
                data = self._dataFromXml(item, parent)
                if data:
                    self.listingReady.emit(data)

    def _dataFromXml(self, item, parent=None):
        self.scanned += 1
        data = ListingData()

        try:
            data.asin = str(item.ASIN)
            data.title = str(item.ItemAttributes.Title)
        except AttributeError:
            return None

        data.salesrank = int(getattr(item, 'SalesRank', 0))
        if not data.salesrank:
            data.salesrank = int(getattr(parent, 'SalesRank', 0))

        data.productgroup = str(getattr(item.ItemAttributes, 'ProductGroup', 'N/A'))

        data.make = str(getattr(item.ItemAttributes, 'Brand', ''))
        if not data.make:
            data.make = str(getattr(item.ItemAttributes, 'Manufacturer', ''))

        data.upc = int(getattr(item.ItemAttributes, 'UPC', 0))
        data.model = str(getattr(item.ItemAttributes, 'Model', ''))
        if not data.model:
            data.model = str(getattr(item.ItemAttributes, 'MPN', ''))

        if hasattr(item.ItemAttributes, 'ItemDimensions'):
            data.length = float(getattr(item.ItemAttributes.ItemDimensions, 'Length', 0))
            data.width = float(getattr(item.ItemAttributes.ItemDimensions, 'Width', 0))
            data.height = float(getattr(item.ItemAttributes.ItemDimensions, 'Height', 0))
            data.weight = float(getattr(item.ItemAttributes.ItemDimensions, 'Weight', 0))

        data.url = str(getattr(item, 'DetailPageURL', ''))

        try:
            data.offers = int(item.OfferSummary.TotalNew)
        except:
            data.offers = 0

        try:
            data.price = float(item.OfferSummary.LowestNewPrice.Amount) / 100
        except AttributeError:
            data.price = 0

        try:
            data.merchant = str(item.Offers.Offer.Merchant.Name)
        except AttributeError:
            data.merchant = 'N/A'

        try:
            data.prime = bool(item.Offers.Offer.OfferListing.IsEligibleForPrime)
        except AttributeError:
            data.prime = False

        return data

    def _bottlenose_error_handler(self, err):
        # Pretty much copied from the bottlenose docs
        ex = err['exception']
        message = repr(ex)
        if isinstance(ex, HTTPError):
            message += ' code ' + str(ex.code)

            if ex.code == 503 and self.retries < 3:
                self.message.emit(message + ', waiting...')
                time.sleep(random.expovariate(0.1))
                self._retries += 1
                return True

        self.retries = 0
        self.message.emit(message)