from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
)

from packages.Startup import GlobalFiles
from packages.Startup.DependencyInstaller import DependencyInstaller
from packages.Startup.UpdateChecker import (
    UpdateChecker,
    installed_mkvtoolnix_version,
    is_newer_version,
)
from packages.Startup.Version import Version
from packages.Widgets.UpdateAvailableMessage import show_update_report


class ApplicationStatusToolbar(QFrame):
    """Persistent dependency and update state for the main workspace."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("applicationStatusBar")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._show_update_result = False
        self._available_mkvtoolnix_version = ""

        self.dependency_status = QLabel()
        self.dependency_status.setObjectName("dependencyStatusLabel")
        self.dependency_status.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        self.dependency_progress = QProgressBar()
        self.dependency_progress.setObjectName("dependencyProgress")
        self.dependency_progress.setTextVisible(True)
        self.dependency_progress.setFixedWidth(170)
        self.dependency_progress.hide()

        self.dependency_action = QPushButton("Download latest MKVToolNix")
        self.dependency_action.setObjectName("statusActionButton")

        self.separator = QFrame()
        self.separator.setObjectName("statusSeparator")
        self.separator.setFrameShape(QFrame.Shape.VLine)

        self.update_status = QLabel("Updates not checked")
        self.update_status.setObjectName("updateStatusLabel")
        self.update_status.setToolTip(
            "Checks MKV Muxing Batch GUI and MKVToolNix stable releases"
        )
        self.check_updates_button = QPushButton("Check for Updates")
        self.check_updates_button.setObjectName("statusActionButton")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 7, 8, 7)
        layout.setSpacing(9)
        layout.addWidget(self.dependency_status, 1)
        layout.addWidget(self.dependency_progress)
        layout.addWidget(self.dependency_action)
        layout.addWidget(self.separator)
        layout.addWidget(self.update_status)
        layout.addWidget(self.check_updates_button)

        self.installer = DependencyInstaller(parent=self)
        self.update_checker = UpdateChecker(parent=self)
        self.dependency_action.clicked.connect(self.install_latest)
        self.check_updates_button.clicked.connect(
            lambda: self.check_for_updates(always_show=True)
        )
        self.installer.progress.connect(self._install_progress)
        self.installer.finished.connect(self._install_finished)
        self.installer.failed.connect(self._install_failed)
        self.update_checker.finished.connect(self._update_check_finished)
        self.refresh_dependency_status()

    @staticmethod
    def _set_status_level(label, level):
        label.setProperty("statusLevel", level)
        label.style().unpolish(label)
        label.style().polish(label)

    def refresh_dependency_status(self, discover=False):
        if discover:
            GlobalFiles.refresh_tools()
        missing_tools = GlobalFiles.get_missing_tools()
        if missing_tools:
            self.dependency_status.setText(
                "●  MKVToolNix missing: " + ", ".join(missing_tools)
            )
            self.dependency_status.setToolTip(GlobalFiles.get_missing_tools_error())
            self._set_status_level(self.dependency_status, "error")
            self.dependency_action.setText("Download latest MKVToolNix")
            self.dependency_action.show()
            return

        installed_version, display_version = installed_mkvtoolnix_version(
            GlobalFiles.MKVMERGE_VERSION,
            GlobalFiles.MKVPROPEDIT_VERSION,
        )
        display_version = display_version or installed_version or "detected"
        self.dependency_status.setText(f"●  MKVToolNix {display_version} · Ready")
        self.dependency_status.setToolTip(
            f"mkvmerge: {GlobalFiles.MKVMERGE_PATH}\n"
            f"mkvpropedit: {GlobalFiles.MKVPROPEDIT_PATH}"
        )
        self._set_status_level(self.dependency_status, "ok")
        if (
            self._available_mkvtoolnix_version
            and is_newer_version(
                self._available_mkvtoolnix_version, installed_version
            )
        ):
            self.dependency_action.setText(
                f"Update to {self._available_mkvtoolnix_version}"
            )
            self.dependency_action.show()
        else:
            self.dependency_action.hide()

    def install_latest(self):
        if not self.installer.install():
            return False
        self.dependency_action.setEnabled(False)
        self.check_updates_button.setEnabled(False)
        self.dependency_progress.setRange(0, 0)
        self.dependency_progress.setFormat("Preparing…")
        self.dependency_progress.show()
        self.dependency_status.setText("●  Finding the latest MKVToolNix release…")
        self._set_status_level(self.dependency_status, "working")
        return True

    def _install_progress(self, percent, message):
        self.dependency_status.setText(f"●  {message}…")
        self._set_status_level(self.dependency_status, "working")
        if percent < 0:
            self.dependency_progress.setRange(0, 0)
            self.dependency_progress.setFormat("Working…")
        else:
            self.dependency_progress.setRange(0, 100)
            self.dependency_progress.setValue(percent)
            self.dependency_progress.setFormat("%p%")

    def _install_finished(self, result):
        GlobalFiles.MKVMERGE_PATH = str(result.mkvmerge_path)
        GlobalFiles.MKVMERGE_VERSION = result.mkvmerge_version
        GlobalFiles.MKVPROPEDIT_PATH = str(result.mkvpropedit_path)
        GlobalFiles.MKVPROPEDIT_VERSION = result.mkvpropedit_version
        GlobalFiles.ENVIRONMENT = GlobalFiles.get_tool_environment(result.mkvmerge_path)
        self._available_mkvtoolnix_version = ""
        self.dependency_progress.hide()
        self.dependency_action.setEnabled(True)
        self.check_updates_button.setEnabled(True)
        self.refresh_dependency_status()
        self.update_status.setText(f"MKVToolNix {result.version} installed")
        self._set_status_level(self.update_status, "ok")

        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Information)
        message.setWindowTitle("MKVToolNix Installed")
        message.setText(f"MKVToolNix {result.version} is ready to use.")
        message.setInformativeText(
            "The downloaded tools were verified against publisher metadata and "
            "are stored in your application data folder."
        )
        message.exec()
        self.check_for_updates(always_show=False)

    def _install_failed(self, error_message):
        self.dependency_progress.hide()
        self.dependency_action.setEnabled(True)
        self.check_updates_button.setEnabled(True)
        self.refresh_dependency_status()
        self.update_status.setText("MKVToolNix download failed")
        self._set_status_level(self.update_status, "error")

        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Critical)
        message.setWindowTitle("MKVToolNix Download Failed")
        message.setText("MKVToolNix could not be installed automatically.")
        message.setInformativeText(error_message)
        message.exec()
        self.check_for_updates(always_show=False)

    def check_for_updates(self, always_show=False):
        if self.installer.installing:
            return False
        if not self.update_checker.check(
            Version,
            GlobalFiles.MKVMERGE_VERSION,
            GlobalFiles.MKVPROPEDIT_VERSION,
        ):
            return False
        self._show_update_result = always_show
        self.check_updates_button.setEnabled(False)
        self.check_updates_button.setText("Checking…")
        self.update_status.setText("Checking for updates…")
        self._set_status_level(self.update_status, "working")
        return True

    def _update_check_finished(self, report):
        self.check_updates_button.setEnabled(not self.installer.installing)
        self.check_updates_button.setText("Check for Updates")
        mkvtoolnix_updates = [
            update for update in report.updates if update.component == "MKVToolNix"
        ]
        if mkvtoolnix_updates:
            self._available_mkvtoolnix_version = mkvtoolnix_updates[0].latest_version
        else:
            self._available_mkvtoolnix_version = ""
        if not self.installer.installing:
            self.refresh_dependency_status()

        self.update_status.setToolTip("")

        if report.updates:
            names = ", ".join(update.component for update in report.updates)
            self.update_status.setText(f"Update available: {names}")
            self._set_status_level(self.update_status, "warning")
        elif report.errors:
            self.update_status.setText("Update check incomplete")
            self.update_status.setToolTip("Could not check: " + ", ".join(report.errors))
            self._set_status_level(self.update_status, "warning")
        elif report.missing:
            self.update_status.setText("Application is up to date")
            self._set_status_level(self.update_status, "ok")
        else:
            self.update_status.setText("All software is up to date")
            self._set_status_level(self.update_status, "ok")

        show_update_report(
            report,
            parent=self,
            always_show=self._show_update_result,
            update_handler=self._handle_update,
        )
        self._show_update_result = False

    def _handle_update(self, update):
        if update.component == "MKVToolNix":
            self.install_latest()
        else:
            QDesktopServices.openUrl(QUrl(update.download_url))
