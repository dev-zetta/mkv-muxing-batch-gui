from PySide6.QtWidgets import QMessageBox


class MissingFilesMessage(QMessageBox):
    def __init__(self, error_message, parent=None):
        super().__init__(parent)
        self.setIcon(QMessageBox.Icon.Warning)
        self.setText("MKVToolNix is not available")
        self.setInformativeText(error_message)
        self.setWindowTitle("Missing Dependency")
        self.download_button = self.addButton(
            "Download MKVToolNix",
            QMessageBox.ButtonRole.ActionRole,
        )
        self.retry_button = self.addButton(
            "Check Again",
            QMessageBox.ButtonRole.ActionRole,
        )
        self.continue_button = self.addButton(
            "Continue Without It",
            QMessageBox.ButtonRole.RejectRole,
        )
        self.setDefaultButton(self.download_button)
        self.setEscapeButton(self.continue_button)

    def execute(self):
        self.exec()
        clicked_button = self.clickedButton()
        if clicked_button is self.download_button:
            return "download"
        if clicked_button is self.retry_button:
            return "retry"
        return "continue"
