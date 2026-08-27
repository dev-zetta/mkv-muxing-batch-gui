from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox


class UpdateAvailableMessage(QMessageBox):
    def __init__(self, updates, errors=(), parent=None):
        super().__init__(parent)
        self.setIcon(QMessageBox.Icon.Information)
        self.setWindowTitle("Updates Available")
        self.setText("Newer software is available")
        self.setInformativeText("\n".join(
            f"{update.component}: {update.current_version} → {update.latest_version}"
            for update in updates
        ))
        self._download_buttons = {}
        for update in updates:
            button = self.addButton(
                f"Open {update.component} Download",
                QMessageBox.ButtonRole.ActionRole,
            )
            self._download_buttons[button] = update.download_url
        self.addButton(QMessageBox.StandardButton.Close)
        if errors:
            self.setDetailedText(
                "The following checks could not be completed: " + ", ".join(errors)
            )

    def execute(self):
        self.exec()
        download_url = self._download_buttons.get(self.clickedButton())
        if download_url:
            QDesktopServices.openUrl(QUrl(download_url))


def show_update_report(report, parent=None, always_show=False):
    if report.updates:
        UpdateAvailableMessage(report.updates, report.errors, parent=parent).execute()
        return
    if not always_show:
        return

    message = QMessageBox(parent)
    if report.errors:
        message.setIcon(QMessageBox.Icon.Warning)
        message.setWindowTitle("Update Check Incomplete")
        message.setText("Some update checks could not be completed.")
        message.setInformativeText(
            "Could not fully check: " + ", ".join(report.errors) + ".\n"
            "Install missing dependencies or check your internet connection, then try again."
        )
    else:
        message.setIcon(QMessageBox.Icon.Information)
        message.setWindowTitle("No Updates Available")
        message.setText("MKV Muxing Batch GUI and MKVToolNix are up to date.")
    message.exec()
