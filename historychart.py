from PyQt5.QtCore import *
from PyQt5.QtChart import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class Callout(QGraphicsItem):

    def __init__(self, parent = None):
        super(Callout, self).__init__(parent)

        self.text = ''
        self.textrect = QRectF()

        self.anchor = QPointF()
        self.rect = QRectF()
        self.font = QFont()

    def setText(self, text):
        self.text = text
        metrics = QFontMetrics(self.font)

        self.textrect = metrics.boundingRect(QRect(0, 0, 150, 150), Qt.AlignLeft, self.text)
        self.prepareGeometryChange()
        self.rect = QRectF(self.textrect.adjusted(-5, -5, 5, 5))

    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget):
        painter.setBrush(QColor(Qt.white))
        painter.drawRect(self.rect)
        painter.drawText(self.textrect, Qt.AlignCenter | Qt.AlignVCenter, self.text)

class ProductHistoryChart(QChart):

    def __init__(self, parent=None):
        super(ProductHistoryChart, self).__init__(parent)

        self.model = None

        rcolor = QColor(Qt.darkCyan)
        pcolor = QColor(Qt.darkGreen)
        ocolor = QColor(Qt.darkMagenta)

        # Create the axes and add them to the chart
        self.timeAxis = QDateTimeAxis()
        self.timeAxis.setFormat('M/dd hh:mm')
        self.timeAxis.setTitleText('Date/Time')
        self.addAxis(self.timeAxis, Qt.AlignBottom)
        self.timeAxis.minChanged.connect(self.loadHistoryUntil)

        self.rankAxis = QValueAxis()
        self.rankAxis.setLabelFormat('%\'i')
        self.rankAxis.setTitleText('Sales Rank')
        self.rankAxis.setLinePenColor(rcolor)
        self.rankAxis.setLabelsColor(rcolor)
        self.addAxis(self.rankAxis, Qt.AlignLeft)

        self.priceAxis = QValueAxis()
        self.priceAxis.setLabelFormat('$%.2f')
        self.priceAxis.setTitleText('Price')
        self.priceAxis.setLinePenColor(pcolor)
        self.priceAxis.setLabelsColor(pcolor)
        self.addAxis(self.priceAxis, Qt.AlignRight)

        self.offersAxis = QValueAxis()
        self.offersAxis.setLabelFormat('%i')
        self.offersAxis.setTitleText('Offers')
        self.offersAxis.setLinePenColor(ocolor)
        self.offersAxis.setLabelsColor(ocolor)
        self.addAxis(self.offersAxis, Qt.AlignRight)

        # Create the series, add them to the chart, and attach the axes.
        self.rankLine = QLineSeries()
        self.addSeries(self.rankLine)
        self.rankLine.attachAxis(self.timeAxis)
        self.rankLine.attachAxis(self.rankAxis)
        self.rankLine.setColor(rcolor)

        self.rankPoints = QScatterSeries()
        self.addSeries(self.rankPoints)
        self.rankPoints.attachAxis(self.timeAxis)
        self.rankPoints.attachAxis(self.rankAxis)
        self.rankPoints.setPen(QPen(Qt.NoPen))
        self.rankPoints.setColor(rcolor)
        self.rankPoints.setMarkerSize(6)
        self.rankPoints.setPointsVisible(True)

        self.priceLine = QLineSeries()
        self.addSeries(self.priceLine)
        self.priceLine.attachAxis(self.priceAxis)
        self.priceLine.attachAxis(self.timeAxis)
        self.priceLine.setColor(pcolor)

        self.pricePoints = QScatterSeries()
        self.addSeries(self.pricePoints)
        self.pricePoints.attachAxis(self.priceAxis)
        self.pricePoints.attachAxis(self.timeAxis)
        self.pricePoints.setPen(QPen(Qt.NoPen))
        self.pricePoints.setColor(pcolor)
        self.pricePoints.setMarkerSize(6)
        self.pricePoints.setPointsVisible(True)

        self.offerLine = QLineSeries()
        self.addSeries(self.offerLine)
        self.offerLine.attachAxis(self.offersAxis)
        self.offerLine.attachAxis(self.timeAxis)
        self.offerLine.setColor(ocolor)

        self.offerPoints = QScatterSeries()
        self.addSeries(self.offerPoints)
        self.offerPoints.setPen(QPen(Qt.NoPen))
        self.offerPoints.setColor(ocolor)
        self.offerPoints.setMarkerSize(6)
        self.offerPoints.attachAxis(self.offersAxis)
        self.offerPoints.attachAxis(self.timeAxis)
        self.offerPoints.setPointsVisible(True)

        # Chart set-up
        self.legend().hide()
        self.setFlags(QGraphicsItem.ItemIsFocusable | QGraphicsItem.ItemIsSelectable)
        self.acceptHoverEvents()

        self.rankPoints.hovered.connect(self.seriesHovered)
        self.pricePoints.hovered.connect(self.seriesHovered)
        self.offerPoints.hovered.connect(self.seriesHovered)
        self.callout = Callout(self)

    def seriesHovered(self, point, show):
        if show:
            timestamp = QDateTime.fromMSecsSinceEpoch(point.x()).toString('M/d H:mm')

            series = self.sender()
            if series is self.rankPoints:
                value = 'Rank: {:,}'.format(int(point.y()))
            elif series is self.pricePoints:
                value = 'Price: ${:,.2f}'.format(point.y())
            elif series is self.offerPoints :
                value = 'Offers: {:,}'.format(int(point.y()))
            else:
                value = ':-('

            self.callout.setText('{}\n{}'.format(timestamp, value))
            self.callout.setPos(self.mapToPosition(point, self.sender()) + QPointF(20, -15))
            self.callout.setZValue(11)
            self.callout.show()
        else:
            self.callout.hide()

    def setModel(self, model):
        self.model = model

        self.modelUpdated()
        self.model.modelReset.connect(self.modelUpdated)

    def modelUpdated(self):
        self.rankLine.clear()
        self.rankPoints.clear()
        self.priceLine.clear()
        self.pricePoints.clear()
        self.offerLine.clear()
        self.offerPoints.clear()

        last = self.model.record(0).value('Timestamp')
        if last:
            time = QDateTime.fromTime_t(last, Qt.LocalTime).addDays(-7)
        else:
            time = QDateTime.currentDateTimeUtc().addDays(-7)

        self.loadHistoryUntil(time)
        self.resetAxes()

    def loadHistoryUntil(self, cutoff=QDateTime.fromTime_t(0, Qt.UTC)):

        if self.rankPoints.count():
            last = self.rankPoints.at(self.rankPoints.count() - 1).x()
        else:
            last = QDateTime.currentDateTime().toMSecsSinceEpoch()

        earliest = QDateTime.fromMSecsSinceEpoch(last, Qt.LocalTime)
        earliest = earliest.toTimeSpec(Qt.UTC)
        earliest = earliest.toTime_t()

        cutoff = cutoff.toTimeSpec(Qt.UTC)
        cutoff = cutoff.toTime_t()

        for row in range(self.rankPoints.count(), self.model.rowCount()):
            record = self.model.record(row)

            time = record.value('Timestamp')
            if time >= earliest:
                continue
            elif time < cutoff:
                return

            time = QDateTime.fromTime_t(time, Qt.UTC)
            time.toTimeSpec(Qt.LocalTime)
            time = time.toMSecsSinceEpoch()

            self.rankPoints.append(time, record.value('SalesRank'))
            self.rankLine.append(time, record.value('SalesRank'))
            self.pricePoints.append(time, record.value('Price'))
            self.priceLine.append(time, record.value('Price'))
            self.offerPoints.append(time, record.value('Offers'))

            if self.offerLine.count() > 1:
                prev = self.offerLine.at(self.offerLine.count() - 1)
                self.offerLine.append(prev.x(), record.value('Offers'))

            self.offerLine.append(time, record.value('Offers'))

    def resetAxes(self):
        r = self.rankPoints.pointsVector()
        p = self.pricePoints.pointsVector()
        o = self.offerPoints.pointsVector()

        # If there is only one data point, set the min and max to the day before and the day after.
        if len(r) == 1:
            tmin = QDateTime.fromMSecsSinceEpoch(r[0].x(), Qt.LocalTime).addDays(-1)
            tmax = QDateTime.fromMSecsSinceEpoch(r[0].x(), Qt.LocalTime).addDays(1)
        else:
            tmin = min(r, key=lambda pt: pt.x(), default=QPointF(QDateTime.currentDateTime().addDays(-1).toMSecsSinceEpoch(), 0)).x()
            tmax = max(r, key=lambda pt: pt.x(), default=QPointF(QDateTime.currentDateTime().addDays(1).toMSecsSinceEpoch(), 0)).x()
            tmin = QDateTime.fromMSecsSinceEpoch(tmin, Qt.LocalTime)
            tmax = QDateTime.fromMSecsSinceEpoch(tmax, Qt.LocalTime)

        self.timeAxis.setMin(tmin)
        self.timeAxis.setMax(tmax)

        # Find the minimum and maximum values in each series
        srmin = min(r, key=lambda pt: pt.y(), default=QPointF(0, 0))
        srmax = max(r, key=lambda pt: pt.y(), default=QPointF(0, 0))

        pmin = min(p, key=lambda pt: pt.y(), default=QPointF(0, 0))
        pmax = max(p, key=lambda pt: pt.y(), default=QPointF(0, 0))

        omin = min(o, key=lambda pt: pt.y(), default=QPointF(0, 0))
        omax = max(o, key=lambda pt: pt.y(), default=QPointF(0, 0))

        # Scale the mins and maxes to 'friendly' values for the axes
        scalemin = lambda v, step: ((v - step / 2) // step) * step
        scalemax = lambda v, step: ((v + step / 2) // step + 1) * step
        onlypositive = lambda v: v if v >= 0 else 0

        srmin = onlypositive(scalemin(srmin.y(), 1000))
        srmax = scalemax(srmax.y(), 1000)

        pmin = onlypositive(scalemin(pmin.y(), 5))
        pmax = scalemax(pmax.y(), 5)

        omin = onlypositive(scalemin(omin.y(), 2))
        omax = scalemax(omax.y(), 5)

        # Set the axes' mins and maxes
        self.rankAxis.setMin(srmin)
        self.rankAxis.setMax(srmax)

        self.priceAxis.setMin(pmin)
        self.priceAxis.setMax(pmax)

        self.offersAxis.setMin(omin)
        self.offersAxis.setMax(omax)

    def sceneEvent(self, event):
        if event.type() == QEvent.GraphicsSceneWheel and event.orientation() == Qt.Vertical:
            self.zoom(1.1 if event.delta() > 0 else 0.9)
            return True

        if event.type() == QEvent.GraphicsSceneMouseDoubleClick:
            self.zoomReset()
            self.resetAxes()
            return True

        if event.type() == QEvent.GraphicsSceneMouseMove:
            delta = event.pos() - event.lastPos()
            self.scroll(-delta.x(), delta.y())
            return True

        return super(ProductHistoryChart, self).sceneEvent(event)
