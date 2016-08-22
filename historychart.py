import math

from PyQt5.QtCore import *
from PyQt5.QtChart import *
from PyQt5.QtGui import *


class ProductHistoryChart(QChart):

    def __init__(self, parent=None):
        super(ProductHistoryChart, self).__init__(parent)

        self.model = None

        self.timeAxis = QDateTimeAxis()
        self.timeAxis.setFormat('MM/dd hh:mm')
        self.timeAxis.setTitleText('Date/Time')
        self.addAxis(self.timeAxis, Qt.AlignBottom)

        self.rankAxis = QValueAxis()
        self.rankAxis.setLabelFormat('%\'u')
        self.rankAxis.setTitleText('Sales Rank')
        self.addAxis(self.rankAxis, Qt.AlignLeft)

        self.priceAxis = QValueAxis()
        self.priceAxis.setLabelFormat('$%.2f')
        self.priceAxis.setTitleText('Price')
        self.addAxis(self.priceAxis, Qt.AlignRight)

        self.offersAxis = QValueAxis()
        self.offersAxis.setLabelFormat('%u')
        self.offersAxis.setTitleText('Offers')
        self.addAxis(self.offersAxis, Qt.AlignRight)

        self.rankSeries = QLineSeries()
        self.addSeries(self.rankSeries)
        self.rankSeries.attachAxis(self.timeAxis)
        self.rankSeries.attachAxis(self.rankAxis)
        self.rankSeries.setPointsVisible(True)

        self.priceSeries = QLineSeries()
        self.addSeries(self.priceSeries)
        self.priceSeries.attachAxis(self.priceAxis)
        self.priceSeries.attachAxis(self.timeAxis)
        self.priceSeries.setPointsVisible(True)

        self.offerLineSeries = QLineSeries()
        self.addSeries(self.offerLineSeries)
        self.offerLineSeries.attachAxis(self.offersAxis)
        self.offerLineSeries.attachAxis(self.timeAxis)

        self.offerPointSeries = QScatterSeries()
        self.addSeries(self.offerPointSeries)
        self.offerPointSeries.setPen(QPen(Qt.NoPen))
        self.offerPointSeries.setColor(self.offerLineSeries.color())
        self.offerPointSeries.setMarkerSize(6)
        self.offerPointSeries.attachAxis(self.offersAxis)
        self.offerPointSeries.attachAxis(self.timeAxis)
        self.offerPointSeries.setPointsVisible(True)

        self.timedata = []

        self.legend().hide()

    def setModel(self, model):
        self.model = model

    def modelUpdated(self):
        self.rankSeries.clear()
        self.priceSeries.clear()
        self.offerLineSeries.clear()
        self.offerPointSeries.clear()
        self.timedata.clear()

        ranks = []
        prices = []
        offers = []

        for row in range(self.model.rowCount()):
            record = self.model.record(row)

            timestamp = QDateTime.fromString(record.value('Timestamp'), Qt.ISODate)
            timestamp.setTimeSpec(Qt.UTC)
            self.timedata.append(timestamp.toLocalTime().toMSecsSinceEpoch())

            ranks.append(record.value('SalesRank'))
            prices.append(record.value('Price'))
            offers.append(record.value('Offers'))

            self.rankSeries.append(self.timedata[-1], ranks[-1])
            self.priceSeries.append(self.timedata[-1], prices[-1])
            self.offerPointSeries.append(self.timedata[-1], offers[-1])

            point = self.offerLineSeries.at(self.offerLineSeries.count() - 1)
            point.setX(self.timedata[-1])
            self.offerLineSeries.append(point)
            self.offerLineSeries.append(self.timedata[-1], offers[-1])

        self.offerLineSeries.remove(0)

        self.timeAxis.setMin(QDateTime.fromMSecsSinceEpoch(self.timedata[0]).addDays(-1))
        self.timeAxis.setMax(QDateTime.fromMSecsSinceEpoch(self.timedata[-1]).addDays(1))

        self.rankAxis.setMin(0)
        self.rankAxis.setMax((max(ranks) * 1.1 // 1000 + 1) * 1000)

        self.priceAxis.setMin((min(prices) // 5 - 1) * 5)
        self.priceAxis.setMax((max(prices) * 1.1 // 5 + 1) * 5)

        self.offersAxis.setMin(0)
        self.offersAxis.setMax((max(offers) * 1.1 // 5 + 1) * 5)
