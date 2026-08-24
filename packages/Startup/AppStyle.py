"""Application-wide visual styles for the desktop shell.

Qt does not provide native backdrop blur consistently across platforms, so the
glass treatment is intentionally implemented with uniformly tinted translucent
surfaces, thin highlights, and restrained shadows.  There are no gradients in
either theme.
"""


def get_dark_glass_stylesheet():
    return """
    QMainWindow, QDialog {
        background-color: #0b0e12;
        color: #f3f4f7;
    }

    QWidget {
        color: #e8eaf0;
        selection-background-color: #62439d;
        selection-color: #ffffff;
    }

    QFrame#appShell, QWidget#workspace, QFrame#contentArea {
        background-color: #0b0e12;
    }

    QFrame#sidebar {
        background-color: rgba(19, 23, 29, 235);
        border-right: 1px solid #353b45;
    }

    QLabel#brandLabel {
        color: #f7f7fa;
        font-size: 17px;
        font-weight: 700;
    }

    QLabel#brandCaption, QLabel#pageDescription, QLabel#summaryCaption {
        color: #8f96a3;
    }

    QListWidget#navigationList {
        background-color: transparent;
        border: none;
        outline: none;
        padding: 2px 8px;
    }

    QListWidget#navigationList::item {
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 8px;
        min-height: 38px;
        padding: 4px 10px;
        color: #c7cbd3;
    }

    QListWidget#navigationList::item:hover {
        background-color: rgba(255, 255, 255, 12);
        border-color: #343a44;
        color: #ffffff;
    }

    QListWidget#navigationList::item:selected {
        background-color: rgba(91, 58, 145, 190);
        border-color: #7654af;
        color: #ffffff;
    }

    QFrame#pageHeader {
        background-color: rgba(23, 27, 33, 220);
        border: 1px solid #353c47;
        border-radius: 11px;
    }

    QLabel#pageTitle {
        color: #f5f5f8;
        font-size: 24px;
        font-weight: 700;
    }

    QLabel#queueSavedLabel {
        color: #7fdb93;
        font-size: 10px;
        font-weight: 600;
        padding: 3px 0;
    }

    QGroupBox {
        background-color: rgba(23, 27, 33, 225);
        border: 1px solid #353c47;
        border-radius: 11px;
        margin-top: 14px;
        padding: 12px 10px 10px 10px;
        font-weight: 600;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 14px;
        padding: 0 7px;
        color: #f0f1f4;
        background-color: #171b21;
    }

    QFrame#summaryCard {
        background-color: rgba(31, 35, 42, 220);
        border: 1px solid #3a414c;
        border-radius: 9px;
    }

    QLabel#summaryValue {
        color: #f7f7fa;
        font-size: 20px;
        font-weight: 700;
    }

    QLabel#sectionLabel {
        color: #aeb4bf;
        font-size: 10px;
        font-weight: 700;
        padding-top: 6px;
    }

    QPushButton {
        background-color: rgba(37, 41, 49, 225);
        color: #eceef3;
        border: 1px solid #4a515d;
        border-radius: 7px;
        padding: 7px 12px;
        min-height: 22px;
    }

    QPushButton:hover {
        background-color: #302b3c;
        border-color: #7554ab;
        color: #ffffff;
    }

    QPushButton:pressed {
        background-color: #282330;
        border-color: #5d4289;
    }

    QPushButton:disabled {
        background-color: rgba(29, 32, 38, 190);
        border-color: #30353d;
        color: #6f7580;
    }

    QPushButton#primaryActionButton {
        background-color: #5f3f96;
        border-color: #7654ae;
        color: #ffffff;
        font-weight: 600;
    }

    QPushButton#primaryActionButton:hover {
        background-color: #6948a0;
        border-color: #8867bd;
    }

    QPushButton#sidebarActionButton {
        background-color: rgba(255, 255, 255, 9);
        border-color: #353b45;
        text-align: left;
    }

    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QDateEdit, QTimeEdit {
        background-color: rgba(10, 13, 17, 210);
        color: #eef0f4;
        border: 1px solid #454c57;
        border-radius: 6px;
        padding: 6px 8px;
        min-height: 21px;
    }

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
        border-color: #7654ae;
        background-color: rgba(14, 17, 22, 230);
    }

    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled,
    QDoubleSpinBox:disabled {
        background-color: rgba(18, 21, 26, 180);
        border-color: #303640;
        color: #707783;
    }

    QComboBox::drop-down {
        border: none;
        width: 24px;
    }

    QComboBox QAbstractItemView {
        background-color: #171b21;
        color: #e8eaf0;
        border: 1px solid #454c57;
        selection-background-color: #5f3f96;
        outline: none;
    }

    QCheckBox, QRadioButton {
        color: #d6dae2;
        spacing: 7px;
        min-height: 22px;
    }

    QCheckBox::indicator, QRadioButton::indicator {
        width: 16px;
        height: 16px;
        background-color: rgba(10, 13, 17, 210);
        border: 1px solid #59616d;
        border-radius: 4px;
    }

    QCheckBox::indicator:hover, QRadioButton::indicator:hover {
        border-color: #8867bd;
    }

    QCheckBox::indicator:checked, QRadioButton::indicator:checked {
        background-color: #6b49a7;
        border: 3px solid #a388cf;
    }

    QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {
        background-color: #20242b;
        border-color: #343a43;
    }

    QTableView, QTableWidget, QListView, QTreeView, QTreeWidget {
        background-color: rgba(12, 15, 19, 190);
        alternate-background-color: rgba(29, 33, 40, 150);
        color: #e4e7ed;
        border: 1px solid #383f49;
        border-radius: 7px;
        gridline-color: #323842;
        outline: none;
    }

    QTableView::item, QTableWidget::item, QListView::item, QTreeView::item {
        padding: 5px;
    }

    QTableView::item:selected, QTableWidget::item:selected,
    QListView::item:selected, QTreeView::item:selected {
        background-color: #46336a;
        color: #ffffff;
    }

    QHeaderView::section {
        background-color: rgba(29, 33, 40, 235);
        color: #cfd3dc;
        border: none;
        border-right: 1px solid #3b424c;
        border-bottom: 1px solid #3b424c;
        padding: 7px;
        font-weight: 600;
    }

    QProgressBar {
        background-color: #282d35;
        color: #f3f6f8;
        border: 1px solid #3d444f;
        border-radius: 6px;
        min-height: 11px;
        max-height: 16px;
        text-align: center;
    }

    QProgressBar::chunk {
        background-color: #47c5df;
        border-radius: 5px;
    }

    QScrollBar:vertical {
        background-color: transparent;
        width: 10px;
        margin: 2px;
    }

    QScrollBar::handle:vertical {
        background-color: #4b515c;
        border-radius: 4px;
        min-height: 28px;
    }

    QScrollBar:horizontal {
        background-color: transparent;
        height: 10px;
        margin: 2px;
    }

    QScrollBar::handle:horizontal {
        background-color: #4b515c;
        border-radius: 4px;
        min-width: 28px;
    }

    QScrollBar::add-line, QScrollBar::sub-line,
    QScrollBar::add-page, QScrollBar::sub-page {
        background: none;
        border: none;
    }

    QTabWidget::pane {
        background-color: rgba(23, 27, 33, 225);
        border: 1px solid #353c47;
        border-radius: 8px;
    }

    QTabBar::tab {
        background-color: rgba(32, 36, 43, 220);
        border: 1px solid #3a414b;
        color: #b9bec8;
        padding: 7px 13px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }

    QTabBar::tab:selected {
        background-color: #5f3f96;
        border-color: #7654ae;
        color: #ffffff;
    }

    QMenu {
        background-color: #171b21;
        color: #e8eaf0;
        border: 1px solid #444b56;
        padding: 4px;
    }

    QMenu::item:selected {
        background-color: #5f3f96;
        color: #ffffff;
    }

    QToolTip {
        background-color: #20252c;
        color: #f2f3f6;
        border: 1px solid #4d5561;
        padding: 5px;
    }
    """


def get_light_glass_stylesheet():
    """A restrained companion theme so the existing theme toggle still works."""
    return """
    QMainWindow, QDialog, QFrame#appShell, QWidget#workspace, QFrame#contentArea {
        background-color: #eef0f4;
        color: #20242b;
    }
    QFrame#sidebar, QFrame#pageHeader, QGroupBox, QFrame#summaryCard {
        background-color: rgba(255, 255, 255, 235);
        border: 1px solid #cfd4dc;
    }
    QFrame#sidebar { border-right: 1px solid #cbd0d8; }
    QFrame#pageHeader, QGroupBox, QFrame#summaryCard { border-radius: 10px; }
    QLabel#brandLabel, QLabel#pageTitle, QLabel#summaryValue { color: #20242b; font-weight: 700; }
    QLabel#brandLabel { font-size: 17px; }
    QLabel#pageTitle { font-size: 24px; }
    QLabel#summaryValue { font-size: 20px; }
    QLabel#brandCaption, QLabel#pageDescription, QLabel#summaryCaption { color: #707783; }
    QLabel#queueSavedLabel { color: #247a3b; font-weight: 600; }
    QListWidget#navigationList { background: transparent; border: none; outline: none; padding: 2px 8px; }
    QListWidget#navigationList::item { border-radius: 8px; min-height: 38px; padding: 4px 10px; color: #3e4652; }
    QListWidget#navigationList::item:hover { background-color: rgba(73, 55, 105, 20); }
    QListWidget#navigationList::item:selected { background-color: #65469b; color: white; }
    QGroupBox { margin-top: 14px; padding: 12px 10px 10px; font-weight: 600; }
    QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 7px; background-color: #ffffff; }
    QPushButton { background-color: #ffffff; color: #282d35; border: 1px solid #c3c9d2; border-radius: 7px; padding: 7px 12px; min-height: 22px; }
    QPushButton:hover { background-color: #f3eff9; border-color: #7654ae; }
    QPushButton#primaryActionButton { background-color: #65469b; border-color: #65469b; color: white; font-weight: 600; }
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
        background-color: #ffffff; color: #252a32; border: 1px solid #bdc4ce; border-radius: 6px; padding: 6px 8px; min-height: 21px;
    }
    QLineEdit:focus, QComboBox:focus { border-color: #7654ae; }
    QTableView, QTableWidget, QListView, QTreeView, QTreeWidget {
        background-color: rgba(255, 255, 255, 235); alternate-background-color: #f2f4f7; color: #252a32;
        border: 1px solid #cbd0d8; border-radius: 7px; gridline-color: #d8dce2; outline: none;
    }
    QHeaderView::section { background-color: #e8ebf0; color: #3d444f; border: none; border-right: 1px solid #d2d6dd; border-bottom: 1px solid #d2d6dd; padding: 7px; font-weight: 600; }
    QProgressBar { background-color: #d9dde4; border: 1px solid #c4cad3; border-radius: 6px; text-align: center; }
    QProgressBar::chunk { background-color: #2faac5; border-radius: 5px; }
    QTabWidget::pane { background-color: #ffffff; border: 1px solid #cbd0d8; }
    QTabBar::tab { background-color: #e7eaf0; border: 1px solid #cbd0d8; padding: 7px 13px; }
    QTabBar::tab:selected { background-color: #65469b; color: white; }
    QToolTip { background-color: #ffffff; color: #20242b; border: 1px solid #bfc5cf; }
    """
