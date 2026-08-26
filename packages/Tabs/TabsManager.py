from PySide6.QtCore import QPointF, QRectF, Signal, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from packages.Startup import ColorThems
from packages.Startup.Options import Options
from packages.Startup.SetupThems import get_dark_palette, get_light_palette
from packages.Tabs.AttachmentTab.AttachmentSelection import AttachmentSelectionSetting
from packages.Tabs.AudioTab.AudioTabManager import AudioTabManager
from packages.Tabs.ChapterTab.ChapterSelection import ChapterSelectionSetting
from packages.Tabs.MuxSetting.MuxSetting import MuxSettingTab
from packages.Tabs.SettingTab.SettingButton import SettingButton
from packages.Tabs.SubtitleTab.SubtitleTabManager import SubtitleTabManager
from packages.Tabs.VideoTab.VideoSelection import VideoSelectionSetting
from packages.Widgets.ThemeButton import ThemeButton


def get_activate_and_disabled_color_according_to_current_theme():
    if Options.Dark_Mode:
        activate_color = ColorThems.Dark_Text_Color
        disabled_color = ColorThems.Dark_Text_Color_Disabled
    else:
        activate_color = ColorThems.Light_Text_Color
        disabled_color = ColorThems.Light_Text_Color_Disabled
    return activate_color, disabled_color


class TabsManager(QWidget):
    """Sidebar workspace that preserves the old tab manager's public API."""

    currentChanged = Signal(int)
    task_bar_start_muxing_signal = Signal()
    update_task_bar_progress_signal = Signal(int)
    update_task_bar_paused_signal = Signal()
    update_task_bar_clear_signal = Signal()
    theme_changed_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("workspace")

        self.video_tab = VideoSelectionSetting()
        self.subtitle_tab = SubtitleTabManager()
        self.audio_tab = AudioTabManager()
        self.attachment_tab = AttachmentSelectionSetting()
        self.chapter_tab = ChapterSelectionSetting()
        self.mux_setting_tab = MuxSettingTab()
        self.mux_setting_tab.subtitle_directories_validator = self.subtitle_tab.validate_directories_before_queue

        self.tabs_ids = {
            "Video": 0,
            "Subtitle": 1,
            "Audio": 2,
            "Chapter": 3,
            "Attachment": 4,
            "Mux Setting": 5,
        }
        self.tabs_status = [True, True, False, False, False, True]
        self.page_titles = [
            "Videos",
            "Subtitles",
            "Audios",
            "Chapters",
            "Attachments",
            "Mux Queue",
        ]
        self.page_descriptions = [
            "Choose the source videos for this batch.",
            "Match and configure subtitle tracks.",
            "Match and configure external audio tracks.",
            "Match chapter files to the selected videos.",
            "Add fonts, artwork, and other MKV attachments.",
            "Review output behavior, monitor progress, and resume saved work.",
        ]

        self.create_shell()
        self.add_tabs()
        self.connect_signals()
        self.setup_tabs_theme()
        self.navigation.setCurrentRow(0)

    def create_shell(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(218)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(14, 20, 14, 14)
        sidebar_layout.setSpacing(10)

        self.brand_label = QLabel("MKV Muxing Batch")
        self.brand_label.setObjectName("brandLabel")
        self.brand_caption = QLabel("Batch media workspace")
        self.brand_caption.setObjectName("brandCaption")
        sidebar_layout.addWidget(self.brand_label)
        sidebar_layout.addWidget(self.brand_caption)
        sidebar_layout.addSpacing(12)

        self.navigation = QListWidget()
        self.navigation.setObjectName("navigationList")
        self.navigation.setIconSize(QSize(20, 20))
        self.navigation.setSpacing(3)
        self.navigation.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.navigation.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.navigation.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sidebar_layout.addWidget(self.navigation, 1)

        self.theme_button = ThemeButton()
        self.theme_button.setObjectName("sidebarActionButton")
        self.theme_button.setText(" Theme")
        self.setting_button = SettingButton()
        self.setting_button.setObjectName("sidebarActionButton")
        sidebar_layout.addWidget(self.theme_button)
        sidebar_layout.addWidget(self.setting_button)

        self.content_area = QFrame()
        self.content_area.setObjectName("contentArea")
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(14, 14, 14, 14)
        content_layout.setSpacing(12)

        self.page_header = QFrame()
        self.page_header.setObjectName("pageHeader")
        header_layout = QHBoxLayout(self.page_header)
        header_layout.setContentsMargins(18, 12, 18, 12)
        header_layout.setSpacing(12)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(1)
        self.page_title = QLabel()
        self.page_title.setObjectName("pageTitle")
        self.page_description = QLabel()
        self.page_description.setObjectName("pageDescription")
        title_layout.addWidget(self.page_title)
        title_layout.addWidget(self.page_description)
        header_layout.addLayout(title_layout)
        header_layout.addStretch(1)

        self.workspace_status = QLabel("●  Ready")
        self.workspace_status.setObjectName("queueSavedLabel")
        self.workspace_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.workspace_status)

        self.page_stack = ResponsiveStackedWidget()
        self.page_stack.setObjectName("pageStack")
        content_layout.addWidget(self.page_header)
        content_layout.addWidget(self.page_stack, 1)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_area, 1)

    def navigation_icons(self):
        color = "#d9dde5" if Options.Dark_Mode else "#3e4652"
        return [self.make_navigation_icon(kind, color) for kind in (
            "video", "subtitle", "audio", "chapter", "attachment", "queue"
        )]

    @staticmethod
    def make_navigation_icon(kind, color):
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if kind == "video":
            painter.drawRoundedRect(QRectF(3.5, 5, 17, 14), 2, 2)
            painter.setBrush(QColor(color))
            painter.drawPolygon(QPolygonF([
                QPointF(10, 9), QPointF(10, 15), QPointF(15, 12)
            ]))
        elif kind == "subtitle":
            painter.drawRoundedRect(QRectF(3.5, 5, 17, 14), 2, 2)
            font = QFont("Arial", 6)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRectF(4, 5, 16, 14), Qt.AlignmentFlag.AlignCenter, "CC")
        elif kind == "audio":
            painter.drawLine(QPointF(10, 6), QPointF(10, 16))
            painter.drawLine(QPointF(10, 6), QPointF(18, 4))
            painter.drawLine(QPointF(18, 4), QPointF(18, 14))
            painter.setBrush(QColor(color))
            painter.drawEllipse(QRectF(5, 15, 5.5, 4))
            painter.drawEllipse(QRectF(13, 13, 5.5, 4))
        elif kind == "chapter":
            painter.drawPolygon(QPolygonF([
                QPointF(6, 4), QPointF(18, 4), QPointF(18, 20),
                QPointF(12, 16), QPointF(6, 20)
            ]))
        elif kind == "attachment":
            painter.drawArc(QRectF(7, 3, 10, 17), 80 * 16, 245 * 16)
            painter.drawArc(QRectF(9, 6, 6, 12), 80 * 16, 250 * 16)
            painter.drawLine(QPointF(8.3, 18), QPointF(17.5, 8.5))
        elif kind == "queue":
            for y in (6, 12, 18):
                painter.setBrush(QColor(color))
                painter.drawEllipse(QRectF(3, y - 1, 2, 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawLine(QPointF(8, y), QPointF(20, y))

        painter.end()
        return QIcon(pixmap)

    def add_tabs(self):
        pages = [
            self.video_tab,
            self.subtitle_tab,
            self.audio_tab,
            self.chapter_tab,
            self.attachment_tab,
            self.mux_setting_tab,
        ]
        icons = self.navigation_icons()
        for index, (title, page) in enumerate(zip(self.page_titles, pages)):
            item = QListWidgetItem(icons[index], title)
            item.setSizeHint(QSize(180, 44))
            self.navigation.addItem(item)
            self.page_stack.addWidget(page)

    def connect_signals(self):
        self.attachment_tab.activation_signal.connect(self.change_attachment_activated_state)
        self.subtitle_tab.activation_signal.connect(self.change_subtitle_activated_state)
        self.audio_tab.activation_signal.connect(self.change_audio_activated_state)
        self.chapter_tab.activation_signal.connect(self.change_chapter_activated_state)
        self.mux_setting_tab.start_muxing_signal.connect(self.start_muxing)
        self.mux_setting_tab.update_task_bar_progress_signal.connect(self.update_task_bar_progress_signal.emit)
        self.mux_setting_tab.update_task_bar_paused_signal.connect(self.update_task_bar_paused_signal.emit)
        self.mux_setting_tab.update_task_bar_clear_signal.connect(self.update_task_bar_clear_signal.emit)
        self.navigation.currentRowChanged.connect(self.set_current_page)
        self.theme_button.dark_mode_updated_signal.connect(self.update_theme_mode_state)
        self.subtitle_tab.directory_validation_failed_signal.connect(
            lambda: self.setCurrentIndex(self.tabs_ids["Subtitle"])
        )

    def set_current_page(self, index):
        if index < 0 or index >= self.page_stack.count():
            return
        self.page_stack.setCurrentIndex(index)
        self.page_title.setText(self.page_titles[index])
        self.page_description.setText(self.page_descriptions[index])
        if index == self.tabs_ids["Mux Setting"]:
            self.workspace_status.setText("●  Queue saved automatically")
        else:
            self.workspace_status.setText("●  Ready")
        self.current_tab_changed(index)
        self.currentChanged.emit(index)

    def currentIndex(self):
        return self.page_stack.currentIndex()

    def setCurrentIndex(self, index):
        self.navigation.setCurrentRow(index)

    def start_muxing(self):
        self.task_bar_start_muxing_signal.emit()

    def set_tab_color(self, tab_index, color_string):
        item = self.navigation.item(tab_index)
        if item is not None:
            item.setForeground(QBrush(QColor(*color_string)))

    def setup_tabs_theme(self):
        activate_color, disabled_color = get_activate_and_disabled_color_according_to_current_theme()
        for tab_id, active in enumerate(self.tabs_status):
            self.set_tab_color(tab_id, activate_color if active else disabled_color)

    def change_attachment_activated_state(self, new_state):
        self._set_tab_status(self.tabs_ids["Attachment"], new_state)

    def change_subtitle_activated_state(self, new_state):
        self._set_tab_status(self.tabs_ids["Subtitle"], new_state)

    def change_audio_activated_state(self, new_state):
        self._set_tab_status(self.tabs_ids["Audio"], new_state)

    def change_chapter_activated_state(self, new_state):
        self._set_tab_status(self.tabs_ids["Chapter"], new_state)

    def _set_tab_status(self, tab_index, new_state):
        activate_color, disabled_color = get_activate_and_disabled_color_according_to_current_theme()
        self.set_tab_color(tab_index, activate_color if new_state else disabled_color)
        self.tabs_status[tab_index] = new_state

    def update_theme_mode_state(self):
        self.theme_changed_signal.emit()
        self.video_tab.update_theme_mode_state()
        self.subtitle_tab.update_theme_mode_state()
        self.audio_tab.update_theme_mode_state()
        self.attachment_tab.update_theme_mode_state()
        self.mux_setting_tab.update_theme_mode_state()
        for index, icon in enumerate(self.navigation_icons()):
            self.navigation.item(index).setIcon(icon)
        self.setup_tabs_theme()
        self.setPalette(get_dark_palette() if Options.Dark_Mode else get_light_palette())

    def current_tab_changed(self, index):
        if index == self.tabs_ids["Video"]:
            self.video_tab.tab_clicked_signal.emit()
        elif index == self.tabs_ids["Subtitle"]:
            self.subtitle_tab.tab_clicked_signal.emit()
        elif index == self.tabs_ids["Audio"]:
            self.audio_tab.tab_clicked_signal.emit()
        elif index == self.tabs_ids["Attachment"]:
            self.attachment_tab.tab_clicked_signal.emit()
        elif index == self.tabs_ids["Chapter"]:
            self.chapter_tab.tab_clicked_signal.emit()
        elif index == self.tabs_ids["Mux Setting"]:
            self.mux_setting_tab.tab_clicked_signal.emit()

    def set_preset_options(self):
        self.video_tab.set_preset_options()
        self.subtitle_tab.set_preset_options()
        self.audio_tab.set_preset_options()
        self.chapter_tab.set_preset_options()
        self.attachment_tab.set_preset_options()
        self.mux_setting_tab.set_preset_options()


class ResponsiveStackedWidget(QStackedWidget):
    """Avoid forcing the shell to the widest hidden page's size hint."""

    def minimumSizeHint(self):
        return QSize(820, 540)

    def sizeHint(self):
        return QSize(1120, 700)
