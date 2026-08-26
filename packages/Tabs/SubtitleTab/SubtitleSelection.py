from PySide6.QtCore import QFileSystemWatcher, QTimer, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
)

from packages.Startup.Options import Options
from packages.Startup.SetupThems import get_dark_palette, get_light_palette
from packages.Tabs.GlobalSetting import *
from packages.Tabs.SubtitleTab.Widgets.MatchSubtitleLayout import MatchSubtitleLayout
from packages.Tabs.SubtitleTab.Widgets.SubtitleClearButton import SubtitleClearButton
from packages.Tabs.SubtitleTab.Widgets.SubtitleDelayDoubleSpinBox import SubtitleDelayDoubleSpinBox
from packages.Tabs.SubtitleTab.Widgets.SubtitleExtensionsCheckableComboBox import SubtitleExtensionsCheckableComboBox
from packages.Tabs.SubtitleTab.Widgets.SubtitleLanguageComboBox import SubtitleLanguageComboBox
from packages.Tabs.SubtitleTab.Widgets.SubtitleMuxOrderWidget import SubtitleMuxOrderWidget
from packages.Tabs.SubtitleTab.Widgets.SubtitleSetDefaultCheckBox import SubtitleSetDefaultCheckBox
from packages.Tabs.SubtitleTab.Widgets.SubtitleSetForcedCheckBox import SubtitleSetForcedCheckBox
from packages.Tabs.SubtitleTab.Widgets.SubtitleSourceButton import SubtitleSourceButton
from packages.Tabs.SubtitleTab.Widgets.SubtitleSourceLineEdit import SubtitleSourceLineEdit
from packages.Tabs.SubtitleTab.Widgets.SubtitleTrackNameLineEdit import SubtitleTrackNameLineEdit
from packages.Widgets.RefreshFilesButton import RefreshFilesButton
from packages.Widgets.InvalidPathDialog import *
from packages.Widgets.WarningDialog import WarningDialog
from packages.Widgets.YesNoDialog import *


# noinspection PyAttributeOutsideInit
class SubtitleSelectionSetting(QGroupBox):
    tab_clicked_signal = Signal()

    is_there_old_files_signal = Signal(bool)

    def __init__(self, tab_index):
        super().__init__()
        self.tab_index = tab_index
        self.create_properties()
        self.create_global_properties()
        self.create_widgets()
        self.setup_widgets()
        self.connect_signals()

    def create_widgets(self):
        self.subtitle_source_label = QLabel("Subtitle Source Folder:")
        self.subtitle_language_label = QLabel("Language:")
        self.subtitle_extension_label = QLabel("Subtitle Extension:")
        self.subtitle_delay_label = QLabel("Delay:")
        self.subtitle_source_lineEdit = SubtitleSourceLineEdit()
        self.subtitle_source_button = SubtitleSourceButton()
        self.subtitle_clear_button = SubtitleClearButton()
        self.subtitle_refresh_files_button = RefreshFilesButton()
        self.subtitle_directory_status_label = QLabel()
        self.subtitle_directory_status_label.setObjectName("subtitleDirectoryStatus")
        self.subtitle_directory_status_label.setWordWrap(True)
        self.subtitle_directory_status_label.hide()
        self.subtitle_extensions_comboBox = SubtitleExtensionsCheckableComboBox()
        self.subtitle_language_comboBox = SubtitleLanguageComboBox(self.tab_index)
        self.subtitle_track_name_lineEdit = SubtitleTrackNameLineEdit(self.tab_index)
        self.subtitle_delay_spin = SubtitleDelayDoubleSpinBox(self.tab_index)
        self.subtitle_set_forced_checkBox = SubtitleSetForcedCheckBox(self.tab_index)
        self.subtitle_set_default_checkBox = SubtitleSetDefaultCheckBox(self.tab_index)
        self.subtitle_mux_order_widget = SubtitleMuxOrderWidget(self.tab_index)
        self.subtitle_match_layout = MatchSubtitleLayout(parent=self, tab_index=self.tab_index)
        self.subtitle_options_layout = QHBoxLayout()
        self.subtitle_set_default_forced_layout = QHBoxLayout()
        # self.MainLayout = QVBoxLayout()
        self.main_layout = QGridLayout()
        self.setObjectName("main_groupBox")
        self.setStyleSheet(
            "QGroupBox#main_groupBox {subcontrol-origin: margin;left: 3px;padding: 3px 0px 3px 0px;}"
            "QLabel#subtitleDirectoryStatus {color: #d99400; font-weight: 600; padding: 4px 2px;}")
        self.subtitle_match_groupBox = QGroupBox("Subtitle Matching")
        self.subtitle_match_groupBox.setLayout(self.subtitle_match_layout)

    def setup_widgets(self):
        self.setup_subtitle_main_groupBox()
        self.setup_layouts()

    # noinspection PyUnresolvedReferences
    def connect_signals(self):
        # self.subtitle_main_groupBox.toggled.connect(self.activate_tab)
        self.subtitle_source_button.clicked_signal.connect(self.update_folder_path)
        self.subtitle_source_lineEdit.edit_finished_signal.connect(self.update_folder_path)
        self.subtitle_refresh_files_button.clicked_signal.connect(self.update_folder_path)
        self.subtitle_source_lineEdit.set_is_drag_and_drop_signal.connect(self.update_is_drag_and_drop)
        self.subtitle_extensions_comboBox.close_list.connect(self.check_extension_changes)
        self.subtitle_match_layout.sync_subtitle_files_with_global_files_after_swap_delete_signal.connect(
            self.sync_subtitle_files_with_global_files)
        self.tab_clicked_signal.connect(self.tab_clicked)
        self.subtitle_match_layout.subtitle_table.drop_folder_and_files_signal.connect(
            self.update_files_with_drag_and_drop)
        self.subtitle_clear_button.clear_files_signal.connect(self.clear_files)
        self.subtitle_directory_watcher.directoryChanged.connect(self.schedule_directory_check)
        self.subtitle_directory_check_timer.timeout.connect(self.check_folder_for_changes)

    def create_global_properties(self):
        GlobalSetting.SUBTITLE_FILES_LIST[self.tab_index] = []
        GlobalSetting.SUBTITLE_FILES_ABSOLUTE_PATH_LIST[self.tab_index] = []
        GlobalSetting.SUBTITLE_TRACK_NAME[self.tab_index] = ""
        GlobalSetting.SUBTITLE_DELAY[self.tab_index] = 0.0
        GlobalSetting.SUBTITLE_TAB_ENABLED[self.tab_index] = False
        GlobalSetting.SUBTITLE_SET_DEFAULT[self.tab_index] = False
        GlobalSetting.SUBTITLE_SET_FORCED[self.tab_index] = False
        GlobalSetting.SUBTITLE_SET_ORDER[self.tab_index] = -1
        GlobalSetting.SUBTITLE_LANGUAGE[self.tab_index] = Options.CurrentPreset.Default_Subtitle_Language

    def create_properties(self):
        if hasattr(self, "subtitle_directory_watcher"):
            self.stop_watching_subtitle_folder()
        if hasattr(self, "subtitle_directory_status_label"):
            self.clear_directory_stale_state()
        self.folder_path = ""
        self.drag_and_dropped_text = "[Drag & Drop Files]"
        self.files_names_list = []
        self.files_names_absolute_list = []
        self.files_names_absolute_list_with_dropped_files = []
        self.current_subtitle_extensions = Options.CurrentPreset.Default_Subtitle_Extensions
        self.is_drag_and_drop = False
        self.subtitle_directory_is_stale = False
        if not hasattr(self, "subtitle_directory_watcher"):
            self.subtitle_directory_watcher = QFileSystemWatcher(self)
            self.subtitle_directory_check_timer = QTimer(self)
            self.subtitle_directory_check_timer.setSingleShot(True)
            self.subtitle_directory_check_timer.setInterval(900)

    def setup_layouts(self):
        self.setup_subtitle_check_default_forced_layout()
        self.setup_subtitle_options_layout()
        self.setup_main_layout()
        # self.setLayout(self.MainLayout)
        # self.MainLayout.addWidget(self.subtitle_tab_comboBox)
        # self.MainLayout.addWidget(self.subtitle_main_groupBox)

    def setup_subtitle_check_default_forced_layout(self):
        self.subtitle_set_default_forced_layout.addWidget(self.subtitle_set_default_checkBox, stretch=0)
        self.subtitle_set_default_forced_layout.addWidget(self.subtitle_set_forced_checkBox, stretch=0)
        self.subtitle_set_default_forced_layout.addWidget(self.subtitle_mux_order_widget, stretch=3)

    def setup_subtitle_options_layout(self):
        self.subtitle_options_layout.addWidget(self.subtitle_extensions_comboBox, 2)
        self.subtitle_options_layout.addWidget(self.subtitle_language_label)
        self.subtitle_options_layout.addWidget(self.subtitle_language_comboBox, 5)
        self.subtitle_options_layout.addWidget(self.subtitle_track_name_lineEdit, 2)
        self.subtitle_options_layout.addWidget(self.subtitle_delay_label)
        self.subtitle_options_layout.addWidget(self.subtitle_delay_spin)
        self.subtitle_options_layout.addLayout(self.subtitle_set_default_forced_layout, 7)
        self.subtitle_options_layout.addStretch()

    def setup_main_layout(self):
        pass
        self.main_layout.addWidget(self.subtitle_source_label, 0, 0)
        self.main_layout.addWidget(self.subtitle_source_lineEdit, 0, 1, 1, 1)
        self.main_layout.addWidget(self.subtitle_clear_button, 0, 2, 1, 1)
        self.main_layout.addWidget(self.subtitle_refresh_files_button, 0, 3, 1, 1)
        self.main_layout.addWidget(self.subtitle_source_button, 0, 4)
        self.main_layout.addWidget(self.subtitle_extension_label, 1, 0)
        self.main_layout.addLayout(self.subtitle_options_layout, 1, 1, 1, 4)
        self.main_layout.addWidget(self.subtitle_directory_status_label, 2, 0, 1, -1)
        self.main_layout.addWidget(self.subtitle_match_groupBox, 3, 0, 1, -1)

    def setup_subtitle_main_groupBox(self):
        self.setLayout(self.main_layout)

    def update_folder_path(self, new_path: str):
        if new_path != "":
            previous_path = self.folder_path
            self.subtitle_source_lineEdit.set_text_safe_change(new_path)
            if not self.update_files_lists(new_path):
                self.subtitle_source_lineEdit.set_text_safe_change(previous_path)
                return
            self.show_subtitle_files_list()
            self.subtitle_refresh_files_button.update_current_path(new_path=new_path)
            self.subtitle_refresh_files_button.setEnabled(True)
            self.watch_subtitle_folder(new_path)
            self.clear_directory_stale_state()
        else:
            if self.is_drag_and_drop:
                self.subtitle_source_lineEdit.set_text_safe_change(self.drag_and_dropped_text)

    def update_files_lists(self, folder_path):
        if folder_path == "" or folder_path.isspace():
            self.folder_path = ""
            if self.is_drag_and_drop:
                new_files_absolute_path_list = []
                self.files_names_list = []
                current_extensions = self.subtitle_extensions_comboBox.currentData()
                for file_absolute_path in self.files_names_absolute_list_with_dropped_files:
                    if os.path.isdir(file_absolute_path):
                        continue
                    if os.path.getsize(file_absolute_path) == 0:
                        continue
                    temp_file_name = os.path.basename(file_absolute_path)
                    for j in range(len(current_extensions)):
                        temp_file_extension_start_index = temp_file_name.rfind(".")
                        if temp_file_extension_start_index == -1:
                            continue
                        temp_file_extension = temp_file_name[temp_file_extension_start_index + 1:]
                        if temp_file_extension.lower() == current_extensions[j].lower():
                            new_files_absolute_path_list.append(file_absolute_path)
                            self.files_names_list.append(os.path.basename(file_absolute_path))
                            break
                self.subtitle_source_lineEdit.stop_check_path = True
                self.subtitle_source_lineEdit.setText(self.drag_and_dropped_text)
                self.is_drag_and_drop = True
                self.folder_path = ""
                self.files_names_absolute_list = new_files_absolute_path_list.copy()
                self.files_names_absolute_list_with_dropped_files = new_files_absolute_path_list.copy()
                self.subtitle_source_lineEdit.stop_check_path = False
            else:
                self.subtitle_source_lineEdit.set_text_safe_change("")
            return True
        try:
            discovered_files = self.get_files_list(folder_path)
            discovered_absolute_paths = get_files_names_absolute_list(discovered_files, folder_path)
            self.is_drag_and_drop = False
            self.folder_path = folder_path
            self.files_names_list = discovered_files
            self.files_names_absolute_list = discovered_absolute_paths
            self.files_names_absolute_list_with_dropped_files = self.files_names_absolute_list.copy()
            return True
        except Exception as e:
            invalid_path_dialog = InvalidPathDialog(parent=self)
            invalid_path_dialog.execute()
            return False

    def check_extension_changes(self, new_extensions):
        if self.current_subtitle_extensions != new_extensions:
            self.current_subtitle_extensions = new_extensions
            if self.update_files_lists(self.folder_path):
                self.show_subtitle_files_list()
                self.clear_directory_stale_state()

    def get_files_list(self, folder_path):
        temp_files_names = sort_names_like_windows(names_list=os.listdir(folder_path))
        temp_files_names_absolute = get_files_names_absolute_list(temp_files_names, folder_path)
        current_extensions = self.subtitle_extensions_comboBox.currentData()
        result = []
        for i in range(len(temp_files_names)):
            if os.path.isdir(temp_files_names_absolute[i]):
                continue
            if os.path.getsize(temp_files_names_absolute[i]) == 0:
                continue
            for j in range(len(current_extensions)):
                temp_file_extension_start_index = temp_files_names[i].rfind(".")
                if temp_file_extension_start_index == -1:
                    continue
                temp_file_extension = temp_files_names[i][temp_file_extension_start_index + 1:]
                if temp_file_extension.lower() == current_extensions[j].lower():
                    result.append(temp_files_names[i])
                    break
        return result

    def show_subtitle_files_list(self):
        self.update_other_classes_variables()
        self.subtitle_match_layout.show_subtitle_files()

    def update_other_classes_variables(self):
        # self.change_global_last_path_directory()
        self.change_global_subtitle_list()
        self.subtitle_source_button.set_is_there_old_file(len(self.files_names_list) > 0)
        self.subtitle_source_lineEdit.set_is_there_old_file(len(self.files_names_list) > 0)
        self.subtitle_extensions_comboBox.set_is_there_old_file(len(self.files_names_list) > 0)
        self.subtitle_clear_button.set_is_there_old_file(len(self.files_names_list) > 0)
        self.subtitle_source_lineEdit.set_current_folder_path(self.folder_path)
        self.subtitle_source_lineEdit.set_is_drag_and_drop(self.is_drag_and_drop)
        self.subtitle_extensions_comboBox.set_current_folder_path(self.folder_path)
        self.subtitle_extensions_comboBox.set_current_files_list(self.files_names_list)
        self.is_there_old_files_signal.emit(len(self.files_names_list) > 0)

    def clear_files(self):
        self.stop_watching_subtitle_folder()
        self.folder_path = ""
        self.files_names_list = []
        self.files_names_absolute_list = []
        self.files_names_absolute_list_with_dropped_files = []
        self.subtitle_refresh_files_button.update_current_path(new_path="")
        self.subtitle_refresh_files_button.setEnabled(True)
        self.subtitle_source_lineEdit.set_text_safe_change("")
        self.is_drag_and_drop = False
        self.clear_directory_stale_state()
        self.show_subtitle_files_list()

    def watch_subtitle_folder(self, folder_path):
        self.stop_watching_subtitle_folder()
        if folder_path and os.path.isdir(folder_path):
            self.subtitle_directory_watcher.addPath(folder_path)

    def stop_watching_subtitle_folder(self):
        watched_directories = self.subtitle_directory_watcher.directories()
        if watched_directories:
            self.subtitle_directory_watcher.removePaths(watched_directories)
        self.subtitle_directory_check_timer.stop()

    def schedule_directory_check(self, _changed_path=""):
        if self.folder_path and not self.is_drag_and_drop:
            self.subtitle_directory_check_timer.start()

    @staticmethod
    def _file_name_keys(file_names):
        return {os.path.normcase(file_name) for file_name in file_names}

    def check_folder_for_changes(self):
        """Detect directory membership changes without disturbing manual matching."""
        if not self.folder_path or self.is_drag_and_drop:
            return False

        if not os.path.isdir(self.folder_path):
            self.mark_directory_stale(0, len(self.files_names_list), folder_missing=True)
            return True

        try:
            discovered_files = self.get_files_list(self.folder_path)
        except OSError:
            self.mark_directory_stale(0, len(self.files_names_list), folder_missing=True)
            return True

        current_keys = self._file_name_keys(self.files_names_list)
        discovered_keys = self._file_name_keys(discovered_files)
        added_count = len(discovered_keys - current_keys)
        removed_count = len(current_keys - discovered_keys)
        if added_count or removed_count:
            self.mark_directory_stale(added_count, removed_count)
            return True

        self.clear_directory_stale_state()
        if self.folder_path not in self.subtitle_directory_watcher.directories():
            self.subtitle_directory_watcher.addPath(self.folder_path)
        return False

    def mark_directory_stale(self, added_count, removed_count, folder_missing=False):
        self.subtitle_directory_is_stale = True
        if folder_missing:
            message = "Subtitle folder is unavailable. Restore it or choose another folder before adding to the queue."
        else:
            changes = []
            if added_count:
                changes.append(f"{added_count} added")
            if removed_count:
                changes.append(f"{removed_count} removed")
            message = (
                f"Subtitle folder changed ({', '.join(changes)}). "
                "Refresh the files and review the matching before adding to the queue."
            )
        self.subtitle_directory_status_label.setText("⚠  " + message)
        self.subtitle_directory_status_label.setToolTip(message)
        self.subtitle_directory_status_label.show()
        self.subtitle_refresh_files_button.setToolTip(message)

    def clear_directory_stale_state(self):
        self.subtitle_directory_is_stale = False
        self.subtitle_directory_status_label.clear()
        self.subtitle_directory_status_label.hide()
        if not self.is_drag_and_drop:
            self.subtitle_refresh_files_button.setToolTip("Refresh Files")

    def change_global_subtitle_list(self):
        GlobalSetting.SUBTITLE_TAB_ENABLED[self.tab_index] = len(self.files_names_list) > 0
        GlobalSetting.SUBTITLE_FILES_LIST[self.tab_index] = self.files_names_list
        GlobalSetting.SUBTITLE_FILES_ABSOLUTE_PATH_LIST[self.tab_index] = self.files_names_absolute_list

    def show_video_files_list(self):
        self.subtitle_match_layout.show_video_files()

    def activate_tab(self, on):
        if on:
            self.show_video_files_list()
        else:
            self.stop_watching_subtitle_folder()
            self.subtitle_source_lineEdit.set_text_safe_change("")
            self.subtitle_match_layout.clear_tables()
            self.folder_path = ""
            self.files_names_list = []
            self.files_names_absolute_list = []
            self.current_subtitle_extensions = Options.CurrentPreset.Default_Subtitle_Extensions
            self.subtitle_extensions_comboBox.setData(self.current_subtitle_extensions)
            self.subtitle_track_name_lineEdit.setText("")
            self.subtitle_set_forced_checkBox.setChecked(False)
            self.subtitle_set_default_checkBox.setChecked(False)
            self.is_drag_and_drop = False
            self.clear_directory_stale_state()
            self.subtitle_source_lineEdit.set_is_drag_and_drop(False)
            self.subtitle_delay_spin.setValue(0)
            GlobalSetting.SUBTITLE_FILES_LIST[self.tab_index] = []
            GlobalSetting.SUBTITLE_FILES_ABSOLUTE_PATH_LIST[self.tab_index] = []
            GlobalSetting.SUBTITLE_TRACK_NAME[self.tab_index] = ""
            GlobalSetting.SUBTITLE_DELAY[self.tab_index] = 0.0
            GlobalSetting.SUBTITLE_SET_DEFAULT[self.tab_index] = False
            GlobalSetting.SUBTITLE_SET_FORCED[self.tab_index] = False
            GlobalSetting.SUBTITLE_SET_ORDER[self.tab_index] = -1
            GlobalSetting.SUBTITLE_TAB_ENABLED[self.tab_index] = False
            GlobalSetting.SUBTITLE_LANGUAGE[self.tab_index] = ""

    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.buttons() == Qt.RightButton:
            self.subtitle_match_layout.clear_subtitle_selection()
        if (QMouseEvent.buttons() == Qt.RightButton or QMouseEvent.buttons() == Qt.LeftButton) and (
                self.subtitle_source_lineEdit.text() == ""):
            self.subtitle_source_lineEdit.set_text_safe_change(self.folder_path)
        return QWidget.mousePressEvent(self, QMouseEvent)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        super().showEvent(a0)
        self.show_video_files_list()

    def change_global_last_path_directory(self):
        if self.folder_path != "" and not self.folder_path.isspace() and not self.is_drag_and_drop:
            GlobalSetting.LAST_DIRECTORY_PATH = self.folder_path

    def tab_clicked(self):
        self.check_folder_for_changes()
        self.show_subtitle_files_list()
        self.show_video_files_list()
        if not GlobalSetting.JOB_QUEUE_EMPTY:
            self.update_subtitle_set_default_forced_state()
            self.disable_editable_widgets()
        else:
            self.enable_editable_widgets()
            self.check_if_video_modify_old_tracks_activated()
            self.update_subtitle_set_default_forced_state()
            self.subtitle_mux_order_widget.check_current_status()

    def check_if_video_modify_old_tracks_activated(self):
        if GlobalSetting.VIDEO_OLD_TRACKS_SUBTITLES_REORDER_ACTIVATED:
            self.subtitle_mux_order_widget.setToolTip(
                "<nobr><b>[Semi Disabled]</b> Only [At Top] option is available<br>Because you have used <b>Modify Old "
                "Tracks</b> option in Video Tab")

    def update_subtitle_set_default_forced_state(self):
        self.subtitle_set_default_checkBox.update_check_state()
        self.subtitle_set_forced_checkBox.update_check_state()

    def disable_editable_widgets(self):
        self.subtitle_source_lineEdit.setEnabled(False)
        self.subtitle_source_button.setEnabled(False)
        self.subtitle_extensions_comboBox.setEnabled(False)
        self.subtitle_language_comboBox.setEnabled(False)
        self.subtitle_track_name_lineEdit.setEnabled(False)
        self.subtitle_delay_spin.setEnabled(False)
        self.subtitle_set_default_checkBox.setEnabled(False)
        self.subtitle_set_forced_checkBox.setEnabled(False)
        self.setCheckable(False)
        self.subtitle_clear_button.setEnabled(False)
        self.subtitle_mux_order_widget.setEnabled(False)
        self.subtitle_refresh_files_button.setEnabled(False)
        self.subtitle_match_layout.disable_editable_widgets()

    def enable_editable_widgets(self):
        self.subtitle_source_lineEdit.setEnabled(True)
        self.subtitle_source_button.setEnabled(True)
        self.subtitle_extensions_comboBox.setEnabled(True)
        self.subtitle_language_comboBox.setEnabled(True)
        self.subtitle_track_name_lineEdit.setEnabled(True)
        self.subtitle_delay_spin.setEnabled(True)
        self.subtitle_set_default_checkBox.setEnabled(True)
        self.subtitle_set_forced_checkBox.setEnabled(True)
        self.subtitle_clear_button.setEnabled(True)
        self.subtitle_mux_order_widget.setEnabled(True)
        if not self.is_drag_and_drop:
            self.subtitle_refresh_files_button.setEnabled(True)
        else:
            self.disable_subtitle_refresh_button_cause_drag_and_drop()
        self.subtitle_match_layout.enable_editable_widgets()

    def sync_subtitle_files_with_global_files(self):
        self.files_names_list = GlobalSetting.SUBTITLE_FILES_LIST[self.tab_index]
        self.files_names_absolute_list = GlobalSetting.SUBTITLE_FILES_ABSOLUTE_PATH_LIST[self.tab_index]
        self.update_other_classes_variables()

    def update_files_with_drag_and_drop(self, paths_list):
        self.stop_watching_subtitle_folder()
        self.clear_directory_stale_state()
        duplicate_flag = False
        not_duplicate_files_absolute_path_list = []
        not_duplicate_files_list = []
        duplicate_files_list = []
        new_files_absolute_path_list = []
        current_extensions = self.subtitle_extensions_comboBox.currentData()
        for path in paths_list:
            if os.path.isfile(path):
                if os.path.getsize(path) == 0:
                    continue
                temp_file_name = os.path.basename(path)
                for j in range(len(current_extensions)):
                    temp_file_extension_start_index = temp_file_name.rfind(".")
                    if temp_file_extension_start_index == -1:
                        continue
                    temp_file_extension = temp_file_name[temp_file_extension_start_index + 1:]
                    if temp_file_extension.lower() == current_extensions[j].lower():
                        new_files_absolute_path_list.append(path)
                        break
            else:
                new_files_absolute_path_list.extend(
                    sort_names_like_windows(get_files_names_absolute_list(self.get_files_list(path), path)))

        for new_file_name in new_files_absolute_path_list:
            if os.path.basename(new_file_name).lower() in map(str.lower, self.files_names_list):
                duplicate_flag = True
                duplicate_files_list.append(os.path.basename(new_file_name))
            else:
                not_duplicate_files_absolute_path_list.append(new_file_name)
                not_duplicate_files_list.append(os.path.basename(new_file_name))
                self.files_names_list.append(os.path.basename(new_file_name))
        self.subtitle_source_lineEdit.stop_check_path = True
        self.subtitle_source_lineEdit.setText(self.drag_and_dropped_text)
        self.is_drag_and_drop = True
        self.folder_path = ""
        self.files_names_absolute_list_with_dropped_files.extend(not_duplicate_files_absolute_path_list)
        self.files_names_absolute_list.extend(not_duplicate_files_absolute_path_list)
        self.show_subtitle_files_list()
        self.subtitle_source_lineEdit.stop_check_path = False
        if duplicate_flag:
            info_message = "One or more files have the same name with the old files will be " \
                           "skipped:"
            for file_name in duplicate_files_list:
                info_message += "\n" + file_name
            warning_dialog = WarningDialog(window_title="Duplicate files names", info_message=info_message,
                                           parent=self.window())
            warning_dialog.execute_wth_no_block()
        self.disable_subtitle_refresh_button_cause_drag_and_drop()

    def disable_subtitle_refresh_button_cause_drag_and_drop(self):
        self.subtitle_refresh_files_button.setEnabled(False)
        self.subtitle_refresh_files_button.setToolTip("Disabled due to Drag/Drop mode")

    def update_is_drag_and_drop(self, new_state):
        self.is_drag_and_drop = new_state

    def set_default_directory(self):
        self.subtitle_source_lineEdit.set_text_safe_change(Options.CurrentPreset.Default_Subtitle_Directory)
        self.update_folder_path(Options.CurrentPreset.Default_Subtitle_Directory)
        self.subtitle_source_lineEdit.check_new_path()

    def set_preset_options(self):
        self.create_properties()
        self.create_global_properties()
        self.subtitle_language_comboBox.initialize()
        self.subtitle_language_comboBox.set_current_index()
        self.subtitle_extensions_comboBox.set_current_extensions()
        self.set_default_directory()

    def update_theme_mode_state(self):
        if Options.Dark_Mode:
            self.setPalette(get_dark_palette())
        else:
            self.setPalette(get_light_palette())
        self.setStyleSheet(
            "QGroupBox#main_groupBox {subcontrol-origin: margin;left: 3px;padding: 3px 0px 3px 0px;}"
            "QLabel#subtitleDirectoryStatus {color: #d99400; font-weight: 600; padding: 4px 2px;}")
