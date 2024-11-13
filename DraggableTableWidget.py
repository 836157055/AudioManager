from PyQt5.QtWidgets import QTableWidget
from PyQt5.QtCore import QMimeData, QUrl, Qt
from PyQt5.QtGui import QDrag

class DraggableTableWidget(QTableWidget):
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.startDrag(Qt.CopyAction)
        super().mouseMoveEvent(event)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item:
            mimeData = QMimeData()
            file_path = self.item(self.currentRow(), 1).text()
            url = QUrl.fromLocalFile(file_path)
            mimeData.setUrls([url])
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec_(Qt.CopyAction | Qt.MoveAction)