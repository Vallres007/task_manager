import sys
import psutil
import winreg
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget, QVBoxLayout
from PyQt5.QtGui import QPainter, QBrush, QColor, QIcon, QPen
from PyQt5.QtCore import Qt, QTimer, QRect, QEvent
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
        self.setFixedSize(400, 150)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        # Start with a fully transparent widget
        self._opacity = 0
        self.setWindowOpacity(self._opacity)

        # Animation setup for fade-in
        self.animation = QPropertyAnimation(self, b"opacity")
        self.animation.setDuration(0)  # 500 ms duration
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.start()
        self.installEventFilter(self)

    @pyqtProperty(float)
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        self.setWindowOpacity(self._opacity)

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.hide()

    def eventFilter(self, source, event):
        # Override the eventFilter method to listen for specific events
        if event.type() == QEvent.WindowDeactivate:
            # When the widget is deactivated (loses focus), hide it
            self.hide()
            return True
        return super().eventFilter(source, event)

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

        # Background color
        if is_windows_dark_mode():
            bgColor = QColor(35, 39, 43)
            textColor = QColor(255, 255, 255)
        else:
            bgColor = QColor(255, 255, 255)
            textColor = QColor(0, 0, 0)

        painter.fillRect(self.rect(), bgColor)
        painter.setPen(textColor)

        # Circle specs
        circle_diameter = 80
        grey_border_thickness = 6  # Grey border thickness
        grey_color = QColor(200, 200, 200)

        # Font and label setup
        percentage_font = self.font()
        percentage_font.setPointSize(12)
        label_font = self.font()
        label_font.setPointSize(10)
        label_height = 20
        padding = 10

        # Calculations for placement
        vertical_space_needed = circle_diameter + padding + label_height
        circle_top = (self.height() - vertical_space_needed) // 2
        horizontal_space = self.width() - (2 * circle_diameter)
        circle_spacing = int(horizontal_space / 3)

        # Pens for the grey border and the fill
        border_pen = QPen(grey_color, grey_border_thickness)
        border_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(border_pen)

        # Draw the grey border for CPU and RAM
        cpu_rect = QRect(circle_spacing, circle_top, circle_diameter, circle_diameter)
        painter.drawEllipse(cpu_rect)

        ram_rect = QRect(
            circle_spacing * 2 + circle_diameter,
            circle_top,
            circle_diameter,
            circle_diameter,
        )
        painter.drawEllipse(ram_rect)

        # Draw the filled arc for CPU and RAM
        fill_pen = QPen()
        fill_pen.setCapStyle(Qt.RoundCap)

        # CPU Usage Arc
        fill_pen.setColor(self.percentage_to_color(self.cpu_usage))
        fill_pen.setWidth(grey_border_thickness)
        painter.setPen(fill_pen)
        angle = int(360 * self.cpu_usage / 100 * 16)
        painter.drawArc(cpu_rect, 90 * 16, -angle)

        # Draw CPU percentage text
        painter.setPen(textColor)
        painter.setFont(percentage_font)
        painter.drawText(cpu_rect, Qt.AlignCenter, f"{self.cpu_usage}%")

        # CPU Label
        painter.setFont(label_font)
        label_cpu_rect = QRect(
            cpu_rect.left(), cpu_rect.bottom() + padding, circle_diameter, label_height
        )
        painter.drawText(label_cpu_rect, Qt.AlignCenter, "CPU")

        # RAM Usage Arc
        fill_pen.setColor(self.percentage_to_color(self.ram_usage))
        painter.setPen(fill_pen)
        angle = int(360 * self.ram_usage / 100 * 16)
        painter.drawArc(ram_rect, 90 * 16, -angle)

        # Draw RAM percentage text
        painter.setPen(textColor)
        painter.setFont(percentage_font)
        painter.drawText(ram_rect, Qt.AlignCenter, f"{self.ram_usage}%")

        # RAM Label
        painter.setFont(label_font)
        label_ram_rect = QRect(
            ram_rect.left(), ram_rect.bottom() + padding, circle_diameter, label_height
        )
        painter.drawText(label_ram_rect, Qt.AlignCenter, "RAM")

        painter.end()


class SystemTrayApp(QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super(SystemTrayApp, self).__init__(icon, parent)
        self.widget = None  # Don't create the widget yet
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
            if self.widget is not None:
                if self.widget.isVisible():
                    # If the widget is already visible but not active, bring it to the front
                    if not self.widget.isActiveWindow():
                        self.widget.activateWindow()
                    else:
                        self.widget.hide()
                else:
                    self.widget.showNormal()  # This ensures the window is restored and focused if minimized
                    self.widget.activateWindow()
            else:
                self.widget = CircleProgress()
                screen_geometry = QApplication.desktop().availableGeometry()
                x_position = screen_geometry.right() - self.widget.width()
                y_position = screen_geometry.bottom() - self.widget.height()
                self.widget.move(x_position, y_position)
                self.widget.showNormal()
                self.widget.activateWindow()

    def update_stats(self):
        cpu_usage = psutil.cpu_percent(interval=None)
        ram_usage = psutil.virtual_memory().percent

        # Check if widget exists before setting values
        if self.widget is not None:
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
