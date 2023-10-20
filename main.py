import sys
import psutil
import winreg
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget, QVBoxLayout
from PyQt5.QtGui import QPainter, QBrush, QColor, QIcon, QPen
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtCore import QPropertyAnimation
from PyQt5.QtCore import pyqtProperty


def is_windows_dark_mode():
    try:
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(
            registry, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return False


class CircleProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cpu_usage = 0
        self.ram_usage = 0
        self.setFixedSize(240, 110)

        self.setWindowFlags(Qt.FramelessWindowHint)

        # Start with a fully transparent widget
        self._opacity = 0
        self.setWindowOpacity(self._opacity)

        # Animation setup for fade-in
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(500)  # 500 ms duration
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.start()

    @pyqtProperty(float)
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        self.setWindowOpacity(self._opacity)

    def percentage_to_color(self, percentage):
        green_component = 255 - int(2.55 * percentage)
        red_component = int(2.55 * percentage)
        return QColor(red_component, green_component, 0, 150)

    def setValues(self, cpu_value, ram_value):
        self.cpu_usage = cpu_value
        self.ram_usage = ram_value
        self.update()  # Refresh the widget to reflect the new values.

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Determine the background color based on the system's dark mode setting
        if is_windows_dark_mode():
            bgColor = QColor(35, 39, 43)  # Black for dark mode
            textColor = QColor(255, 255, 255)  # White text for dark mode
        else:
            bgColor = QColor(255, 255, 255)  # White for light mode
            textColor = QColor(0, 0, 0)  # Black text for light mode

        painter.fillRect(self.rect(), bgColor)
        painter.setPen(textColor)  # Set the pen color for text

        circle_diameter = 80  # Diameter of the circle
        border_thickness = 4

        # Font for percentage
        percentage_font = self.font()
        percentage_font.setPointSize(12)

        # CPU Circle
        cpu_rect = self.rect().adjusted(
            10,
            10,
            -(self.width() - (10 + circle_diameter)),
            -(self.height() - (10 + circle_diameter)),
        )
        painter.setPen(
            QPen(self.percentage_to_color(self.cpu_usage), border_thickness)
        )  # Border color for CPU circle with thickness
        painter.setBrush(Qt.transparent)  # Transparent fill
        painter.drawEllipse(cpu_rect)
        painter.setFont(percentage_font)
        painter.setPen(textColor)  # Set the text color again for drawing text
        painter.drawText(cpu_rect, Qt.AlignCenter, f"{self.cpu_usage}%")

        label_cpu_rect = QRect(10, 10 + circle_diameter, circle_diameter, 20)
        painter.setFont(self.font())
        painter.drawText(label_cpu_rect, Qt.AlignCenter, "CPU")

        # RAM Circle
        ram_rect = self.rect().adjusted(
            130,
            10,
            -(self.width() - (130 + circle_diameter)),
            -(self.height() - (10 + circle_diameter)),
        )
        painter.setPen(
            QPen(self.percentage_to_color(self.ram_usage), border_thickness)
        )  # Border color for RAM circle with thickness
        painter.setBrush(Qt.transparent)  # Transparent fill
        painter.drawEllipse(ram_rect)
        painter.setFont(percentage_font)
        painter.setPen(textColor)  # Set the text color again for drawing text
        painter.drawText(ram_rect, Qt.AlignCenter, f"{self.ram_usage}%")

        label_ram_rect = QRect(130, 10 + circle_diameter, circle_diameter, 20)
        painter.setFont(self.font())
        painter.drawText(label_ram_rect, Qt.AlignCenter, "RAM")

        painter.end()


class SystemTrayApp(QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super(SystemTrayApp, self).__init__(icon, parent)
        self.widget = CircleProgress()
        menu = QMenu(parent)

        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(sys.exit)

        self.activated.connect(self.on_tray_icon_activated)
        self.setContextMenu(menu)

        # Setup timer for auto-updating stats
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(2000)  # Update every 2 seconds

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.widget.isVisible():
                self.widget.hide()
            else:
                tray_geometry = self.geometry()
                x_position = (
                    tray_geometry.x() - self.widget.width() + tray_geometry.width()
                )
                y_position = tray_geometry.y() - self.widget.height()
                self.widget.move(x_position, y_position)
                self.widget.show()

    def update_stats(self):
        cpu_usage = psutil.cpu_percent(interval=1)
        ram_usage = psutil.virtual_memory().percent
        self.widget.setValues(cpu_usage, ram_usage)

        tooltip_text = f"CPU: {cpu_usage}%\nRAM: {ram_usage}%"
        self.setToolTip(tooltip_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    tray_icon = QApplication.style().standardIcon(QApplication.style().SP_DriveHDIcon)
    tray = SystemTrayApp(tray_icon)
    tray.show()
    sys.exit(app.exec_())
