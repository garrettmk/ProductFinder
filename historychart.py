import math

from PyQt5.QtCore import *
from PyQt5.QtChart import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class ProductHistoryChart(QChart):

    def __init__(self, parent=None):
        super(ProductHistoryChart, self).__init__(parent)

        self.model = None

        # Create the axes and add them to the chart
        self.timeAxis = QDateTimeAxis()
        self.timeAxis.setFormat('MM/dd hh:mm')
        self.timeAxis.setTitleText('Date/Time')
        self.addAxis(self.timeAxis, Qt.AlignBottom)

        self.rankAxis = QValueAxis()
        self.rankAxis.setLabelFormat('%\'i')
        self.rankAxis.setTitleText('Sales Rank')
        self.addAxis(self.rankAxis, Qt.AlignLeft)

        self.priceAxis = QValueAxis()
        self.priceAxis.setLabelFormat('$%.2f')
        self.priceAxis.setTitleText('Price')
        self.addAxis(self.priceAxis, Qt.AlignRight)

        self.offersAxis = QValueAxis()
        self.offersAxis.setLabelFormat('%i')
        self.offersAxis.setTitleText('Offers')
        self.addAxis(self.offersAxis, Qt.AlignRight)

        # Create the series, add them to the chart, and attach the axes.
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

        self.legend().hide()

    def setModel(self, model):
        self.model = model
        self.modelUpdated()
        self.model.modelReset.connect(self.modelUpdated)

    def modelUpdated(self):
        self.rankSeries.clear()
        self.priceSeries.clear()
        self.offerLineSeries.clear()
        self.offerPointSeries.clear()

        for row in range(self.model.rowCount()):
            record = self.model.record(row)

            time = QDateTime.fromString(record.value('Timestamp'), Qt.ISODate)
            time.setTimeSpec(Qt.UTC)
            time = time.toLocalTime().toMSecsSinceEpoch()

            self.rankSeries.append(time, record.value('SalesRank'))
            self.priceSeries.append(time, record.value('Price'))
            self.offerPointSeries.append(time, record.value('Offers'))

            prev = self.offerLineSeries.at(self.offerLineSeries.count() - 1)
            prev.setX(time)
            self.offerLineSeries.append(time, prev.y())
            self.offerLineSeries.append(time, record.value('Offers'))

        self.offerLineSeries.remove(0)

        self.resetAxes()

    def resetAxes(self):
        self.timeAxis.setMin(QDateTime.fromMSecsSinceEpoch(self.model.min('Timestamp')).addDays(-1))
        self.timeAxis.setMin(QDateTime.fromMSecsSinceEpoch(self.model.max('Timestamp')).addDays(1))

        self.rankAxis.setMin(0)
        self.rankAxis.setMax((self.model.max('SalesRank') * 1.1 // 1000 + 1) * 1000)

        self.priceAxis.setMin((self.model.min('Price') // 5 - 1) * 5)
        self.priceAxis.setMax((self.model.max('Price') // 5 + 1) * 5)

        self.offersAxis.setMin(0)
        self.offersAxis.setMax((self.model.max('Offers') * 1.1 // 5 + 1) * 5)

    def sceneEvent(self, event):
        if event.type() == QEvent.GraphicsSceneWheel and event.orientation() == Qt.Vertical:
            self.zoom(1.1 if event.delta() > 0 else 0.9)
            return True

        if event.type() == QEvent.GraphicsSceneMouseDoubleClick:
            self.resetAxes()
            return True

        if event.type() == QEvent.GraphicsSceneMouseMove:
            delta = event.pos() - event.lastPos()
            self.scroll(-delta.x(), delta.y())

        return super(ProductHistoryChart, self).sceneEvent(event)
