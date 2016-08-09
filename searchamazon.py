import random
import datetime
import bottlenose

from lxml import objectify
from urllib.request import HTTPError
from PyQt5.QtCore import *


# ----------------------------------------------------------------------------

# These aren't used anymore, but I'm keeping this in the comments because it has
# all the FBA Toolkit tokens nicely laid out. They were a pain to get.
# categoryToFBAToolkit = {
#     'Toys & Games': 'VG95cyAmIEdhbWVz',
#     'Automotive': 'QXV0b21vdGl2ZQ==',
#     'Home Improvements': 'SG9tZSBJbXByb3ZlbWVudHM=',
#     'Kitchen & Dining': 'SG9tZSAmIEtpdGNoZW4=',
#     'Home & Kitchen': 'SG9tZSBhbmQgS2l0Y2hlbg==',
#     'Health & Personal Care': 'SGVhbHRoICYgUGVyc29uYWwgQ2FyZQ==',
#     'Beauty': 'QmVhdXR5',
#     'Sports & Outdoors': 'U3BvcnRzICYgT3V0ZG9vcnM=',
#     'Musical Instruments': 'TXVzaWNhbCBJbnN0cnVtZW50cw==',
#     'Grocery & Gourmet Food': 'R3JvY2VyeSAmIEdvdXJtZXQgRm9vZA==',
#     'Patio, Lawn & Garden': 'UGF0aW8sIExhd24gJiBHYXJkZW4=',
#     'Clothing': 'Q2xvdGhpbmc=',
#     'Pet Supplies': 'UGV0IFN1cHBsaWVz',
#     'Office Products': 'T2ZmaWNlIFByb2R1Y3Rz',
#     'Industrial & Scientific': 'SW5kdXN0cmlhbCAmIFNjaWVudGlmaWM=',
#     'Jewelry': 'SmV3ZWxyeQ==',
#     'Baby': 'QmFieQ==',
#     'Arts, Crafts & Sewing': 'YXJ0cy1jcmFmdHM=',
#     'Video Games': 'VmlkZW8gR2FtZXM=',
#     'Cell Phones & Accessories': 'Q2VsbCBQaG9uZXMgJiBBY2Nlc3Nvcmllcw==',
#     'Electronics': 'RWxlY3Ryb25pY3M=',
#     'Home & Garden': 'SG9tZSBhbmQgR2FyZGVu',
#     'Watches': 'V2F0Y2hlcw==',
#     'Camera & Photo': 'Q2FtZXJhICYgUGhvdG8=',
#     'Computers & Accessories': 'Q29tcHV0ZXJzICYgQWNjZXNzb3JpZXM=',
#     'Software': 'U29mdHdhcmU=',
#     'Appliances': 'QXBwbGlhbmNlcw==',
#     'Music': 'TXVzaWM=',
#     'Movies & TV': 'TW92aWVzICYgVFY='
# }

# --------------------------------------------------------------------------------


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


class SearchRequest(object):

    def __init__(self, keywords=None, indexes=None, minprice=None, maxprice=None):
        self.keywords = keywords
        self.indexes = indexes
        self.minPrice = minprice
        self.maxPrice = maxprice




# ---------------------------------------------------------------------------------------


class SearchAmazon(QObject):

    newResultReady = pyqtSignal(ListingData)
    searchComplete = pyqtSignal()
    searchMessage = pyqtSignal(str)

    def __init__(self, parent=None, config={}):
        super(SearchAmazon, self).__init__(parent)

        self.abort = False
        self.mutex = QMutex()

        self.amazon = bottlenose.Amazon(config['access_key'], config['secret_key'], config['associate_tag'],
                                        Parser=objectify.fromstring, MaxQPS=0.9)
        self._retries = 0


    def asinSearch(self, asins):
        """Schedule a lookup operation for a list of ASINs."""
        self.abort = False
        QMetaObject.invokeMethod(self, '_asinSearch', Qt.QueuedConnection,
                                 Q_ARG(tuple, tuple(asins)))    # Q_ARG can't take a mutable type, so convert to tuple.

    def keywordSearch(self, keywords, searchindexes, minprice=None, maxprice=None):
        """Schedule a search for ``keywords`` in each category in ``searchindexes``."""
        self.abort = False
        QMetaObject.invokeMethod(self, '_keywordSearch', Qt.QueuedConnection,
                                        Q_ARG(str, keywords),
                                        Q_ARG(tuple, tuple(searchindexes)),     # Q_ARG can only take immutable types.
                                        Q_ARG(float, minprice),
                                        Q_ARG(float, maxprice))
    @pyqtSlot()
    def stopSearch(self):
        """Abort the currently running search operation."""
        self.abort = True

    @pyqtSlot(tuple)
    def _asinSearch(self, asins):
        """Perform an ItemLookup request for each ASIN in a list."""
        for asin in asins:
            if self.abort:
                break

            self.searchMessage.emit('Looking up {}...'.format(asin))

            listing = self._item_lookup(asin, ResponseGroup='ItemAttributes,OfferFull,SalesRank,Variations')
            parsedListing = self._parseListing(listing)
            if parsedListing is None:
                self.searchMessage.emit('Parse Error: ' + asin)
            else:
                self.newResultReady.emit(parsedListing)

        self.searchComplete.emit()
        self.searchMessage.emit('Lookup complete. {} results scanned.'.format(asins.index(asin)))

    @pyqtSlot(str, tuple, float, float)
    def _keywordSearch(self, keywords, searchindexes, minprice=None, maxprice=None):
        scanned = 0

        for searchindex in searchindexes:
            if self.abort:
                break

            self.searchMessage.emit('Searching "{}" in {}...'.format(keywords, searchindex))

            options = {}
            if searchindex != 'All' and searchindex != 'Blended':
                if minprice is not None:
                    options['MinimumPrice'] = int(minprice * 100)
                if maxprice is not None and maxprice > 0:
                    options['MaximumPrice'] = int(maxprice * 100)

            maxpages = 5 if searchindex == 'All' else 10
            for page in range(1, maxpages + 1):
                if self.abort:
                    break

                # Get some raw results from Amazon
                results = self._item_search(searchindex, Keywords=keywords, ItemPage=page,
                                            ResponseGroup='ItemAttributes,OfferFull,SalesRank,Variations', **options)
                if results is None:
                    break

                # Parse the results into ListingData objects, and emit() each result
                for searchResult in results:
                    if self.abort:
                        break

                    # Check to see if listing actually refers to a parent item.
                    # If so, do a little sub-search to get it's children
                    parentASIN = str(getattr(searchResult, 'ParentASIN', ''))
                    if parentASIN == searchResult.ASIN:
                        childASINs = map(str, searchResult.xpath('./aws:Variations/aws:Item/aws:ASIN',
                                                                 namespaces={'aws': searchResult.nsmap.get(None)}))

                        for childASIN in childASINs:
                            if self.abort:
                                break

                            childListing = self._item_lookup(childASIN,
                                                             ResponseGroup='ItemAttributes,OfferFull,SalesRank,Variations')
                            parsedListing = self._parseListing(childListing, searchResult)
                            if parsedListing is None:
                                self.searchMessage.emit('Parse Error: ' + getattr(childListing, 'ASIN', 'N/A'))
                            else:
                                self.newResultReady.emit(parsedListing)

                            scanned += 1
                    else:
                        parsedListing = self._parseListing(searchResult)
                        if parsedListing is None:
                            self.searchMessage.emit('Parse error: ' + getattr(searchResult, 'ASIN', 'N/A'))
                        else:
                            self.newResultReady.emit(parsedListing)

                        scanned += 1

        self.searchMessage.emit('Search complete. {} results scanned.'.format(scanned))
        self.searchComplete.emit()

    def _parseListing(self, listing, parent=None):
        if listing is None:
            return

        data = ListingData()

        try:
            data.asin = str(listing.ASIN)
            data.title = str(listing.ItemAttributes.Title)
        except AttributeError:
            return

        data.salesrank = int(getattr(listing, 'SalesRank', 0))
        if not data.salesrank:
            data.salesrank = int(getattr(parent, 'SalesRank', 0))

        data.productgroup = str(getattr(listing.ItemAttributes, 'ProductGroup', 'N/A'))

        data.make = str(getattr(listing.ItemAttributes, 'Brand', ''))
        if not data.make:
            data.make = str(getattr(listing.ItemAttributes, 'Manufacturer', ''))

        data.upc = int(getattr(listing.ItemAttributes, 'UPC', 0))
        data.model = str(getattr(listing.ItemAttributes, 'Model', ''))
        if not data.model:
            data.model = str(getattr(listing.ItemAttributes, 'MPN', ''))

        if hasattr(listing.ItemAttributes, 'ItemDimensions'):
            data.length = float(getattr(listing.ItemAttributes.ItemDimensions, 'Length', 0))
            data.width = float(getattr(listing.ItemAttributes.ItemDimensions, 'Width', 0))
            data.height = float(getattr(listing.ItemAttributes.ItemDimensions, 'Height', 0))
            data.weight = float(getattr(listing.ItemAttributes.ItemDimensions, 'Weight', 0))

        data.url = str(getattr(listing, 'DetailPageURL', ''))

        try:
            data.offers = int(listing.OfferSummary.TotalNew)
        except:
            data.offers = 0

        try:
            data.price = float(listing.OfferSummary.LowestNewPrice.Amount) / 100
        except AttributeError:
            data.price = 0

        try:
            data.merchant = str(listing.Offers.Offer.Merchant.Name)
        except AttributeError:
            data.merchant = 'N/A'

        try:
            data.prime = bool(listing.Offers.Offer.OfferListing.IsEligibleForPrime)
        except AttributeError:
            data.prime = False

        return data

    def _item_search(self, searchindex, **kwargs):
        try:
            return self.amazon.ItemSearch(ErrorHandler=self._error_handler, SearchIndex=searchindex, **kwargs).Items.Item
        except Exception as e:
            self.searchMessage.emit(repr(e))
            return None

    def _item_lookup(self, itemId, **kwargs):
        try:
            return self.amazon.ItemLookup(ErrorHandler=self._error_handler, ItemId=itemId, **kwargs).Items.Item
        except Exception as e:
            self.searchMessage.emit(repr(e))
            return None

    def _error_handler(self, err):
        # Pretty much copied from the bottlenose docs
        ex = err['exception']
        message = repr(ex)
        if isinstance(ex, HTTPError):
            message += ' code ' + str(ex.code)

            if ex.code == 503 and self._retries < 3:
                self.searchMessage.emit(message + ', waiting...')
                time.sleep(random.expovariate(0.1))
                self._retries += 1
                return True

        self._retries = 0
        self.searchMessage.emit(message)
