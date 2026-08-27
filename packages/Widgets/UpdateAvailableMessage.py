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
            action = "Install" if update.component == "MKVToolNix" else "Open"
            button = self.addButton(
                f"{action} {update.component} Update",
                QMessageBox.ButtonRole.ActionRole,
            )
            self._download_buttons[button] = update
        self.addButton(QMessageBox.StandardButton.Close)
        if errors:
            self.setDetailedText(
                "The following checks could not be completed: " + ", ".join(errors)
            )

    def execute(self):
        self.exec()
        return self._download_buttons.get(self.clickedButton())


def show_update_report(report, parent=None, always_show=False, update_handler=None):
    if report.updates:
        selected_update = UpdateAvailableMessage(
            report.updates, report.errors, parent=parent
        ).execute()
        if selected_update:
            if update_handler:
                update_handler(selected_update)
            else:
                QDesktopServices.openUrl(QUrl(selected_update.download_url))
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
    elif report.missing:
        message.setIcon(QMessageBox.Icon.Warning)
        message.setWindowTitle("Dependency Missing")
        message.setText("The application is current, but MKVToolNix is not installed.")
        message.setInformativeText(
            "Use Download latest MKVToolNix in the bottom toolbar to install it."
        )
    else:
        message.setIcon(QMessageBox.Icon.Information)
        message.setWindowTitle("No Updates Available")
        message.setText("MKV Muxing Batch GUI and MKVToolNix are up to date.")
    message.exec()
