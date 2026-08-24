from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from packages.Tabs.GlobalSetting import GlobalSetting
from packages.Widgets.MyDialog import MyDialog


class NameManipulationDialog(MyDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Name Manipulation")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, on=False)

        self.video_title_line_edit = QLineEdit(GlobalSetting.MUX_SETTING_VIDEO_TITLE_TEMPLATE)
        self.audio_name_line_edit = QLineEdit(GlobalSetting.MUX_SETTING_AUDIO_NAME_TEMPLATE)
        self.subtitle_name_line_edit = QLineEdit(GlobalSetting.MUX_SETTING_SUBTITLE_NAME_TEMPLATE)

        for line_edit in (
            self.video_title_line_edit,
            self.audio_name_line_edit,
            self.subtitle_name_line_edit,
        ):
            line_edit.setClearButtonEnabled(True)
            line_edit.setPlaceholderText("Leave blank to keep existing metadata")

        form_layout = QFormLayout()
        form_layout.addRow("Video title:", self.video_title_line_edit)
        form_layout.addRow("Audio track names:", self.audio_name_line_edit)
        form_layout.addRow("Subtitle track names:", self.subtitle_name_line_edit)

        help_label = QLabel(
            "Available placeholders: {old}, {filename}, {stem}, {index}, {language}.\n"
            "Example: {stem} - {language} keeps each video's filename and track language."
        )
        help_label.setWordWrap(True)

        self.clear_button = QPushButton("Clear All")
        self.cancel_button = QPushButton("Cancel")
        self.apply_button = QPushButton("Apply")
        self.apply_button.setDefault(True)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addWidget(help_label)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        self.setMinimumWidth(520)

        self.clear_button.clicked.connect(self.clear_all)
        self.cancel_button.clicked.connect(self.reject)
        self.apply_button.clicked.connect(self.apply)

    def clear_all(self):
        self.video_title_line_edit.clear()
        self.audio_name_line_edit.clear()
        self.subtitle_name_line_edit.clear()

    def apply(self):
        GlobalSetting.MUX_SETTING_VIDEO_TITLE_TEMPLATE = self.video_title_line_edit.text()
        GlobalSetting.MUX_SETTING_AUDIO_NAME_TEMPLATE = self.audio_name_line_edit.text()
        GlobalSetting.MUX_SETTING_SUBTITLE_NAME_TEMPLATE = self.subtitle_name_line_edit.text()
        self.accept()

    def execute(self):
        return self.exec()
