from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


class ThumbnailLoader(QObject):
    loaded = Signal(bytes)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)
        self.reply = None

    def cancel(self):
        reply, self.reply = self.reply, None
        if reply:
            reply.abort()

    def load(self, url):
        self.cancel()
        parsed = QUrl(url or "")
        if parsed.scheme() not in ("http", "https") or not parsed.host():
            return
        request = QNetworkRequest(parsed)
        request.setTransferTimeout(10000)
        reply = self.manager.get(request)
        self.reply = reply
        data = bytearray()

        def read():
            data.extend(bytes(reply.readAll()))
            if len(data) > 5 * 1024 * 1024:
                reply.abort()

        def finish():
            read()
            if self.reply is reply:
                self.reply = None
                if reply.error() == QNetworkReply.NetworkError.NoError and len(data) <= 5 * 1024 * 1024:
                    self.loaded.emit(bytes(data))
            reply.deleteLater()

        reply.readyRead.connect(read)
        reply.finished.connect(finish)
