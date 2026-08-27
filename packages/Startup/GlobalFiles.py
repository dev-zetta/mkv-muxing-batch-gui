import logging
import os
import struct
import subprocess
import sys
from os import listdir
from pathlib import Path
from shutil import which


def create_app_data_folder():
    """
        Returns a parent directory path
        where persistent application data can be stored.

        # linux: ~/.local/share
        # macOS: ~/Library/Application Support
        # windows: C:/Users/<USER>/AppData/Roaming
        """
    custom_data_dir = os.environ.get("MKV_MUXING_BATCH_GUI_DATA_DIR")
    if custom_data_dir:
        my_app_data_folder = Path(custom_data_dir).expanduser()
        my_app_data_folder.mkdir(parents=True, exist_ok=True)
        return my_app_data_folder

    home = Path.home()
    if sys.platform == "win32":
        app_data = home / "AppData/Roaming"
    elif sys.platform == "linux":
        app_data = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share"))
    elif sys.platform == "darwin":
        app_data = home / "Library/Application Support"
    else:
        app_data = home / ".local/share"
    my_app_data_folder = app_data / "MKV Muxing Batch GUI"
    my_app_data_folder.mkdir(parents=True, exist_ok=True)
    return my_app_data_folder


def add_double_quotation(string):
    return "\"" + str(string) + "\""


def get_file_name_absolute_path(file_name, folder_path):
    return os.path.join(Path(folder_path), file_name)


def get_files_names_absolute_list(files_names, folder_path):
    result = []
    for i in range(len(files_names)):
        result.append(get_file_name_absolute_path(file_name=files_names[i], folder_path=folder_path))
    return result


def delete_old_media_files():
    only_media_info_files = get_files_names_absolute_list(files_names=listdir(MediaInfoFolderPath),
                                                          folder_path=MediaInfoFolderPath)
    for file_name in only_media_info_files:
        try:
            os.remove(file_name)
        except Exception as e:
            pass


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    # PyInstaller keeps bundled data under its private runtime directory.
    script_folder = sys._MEIPASS
else:
    # Resolve resources from the package location instead of sys.argv[0].
    # Test runners and launchers replace argv[0], which previously made the
    # application look for Resources beside pytest/python and open a fatal
    # missing-files dialog during import.
    script_folder = str(Path(__file__).resolve().parents[2])
resources_folder = os.path.join(os.path.abspath(script_folder), Path('Resources'))
FontFolderPath = os.path.join(os.path.abspath(resources_folder), Path('Fonts'))
IconFolderPath = os.path.join(os.path.abspath(resources_folder), Path('Icons'))
DLLFolderPath = os.path.join(os.path.abspath(resources_folder), Path('DLL'))
GlobalToolsFolderPath = os.path.join(os.path.abspath(resources_folder), Path('Tools'))
ToolsFolderPath = os.path.join(os.path.abspath(GlobalToolsFolderPath), Path('Windowsx64'))
LanguagesFolderPath = os.path.join(os.path.abspath(resources_folder), Path('Languages'))
LibFolderPath = ""
if sys.platform == "win32":
    if struct.calcsize("P") * 8 == 32:
        ToolsFolderPath = os.path.join(os.path.abspath(GlobalToolsFolderPath), Path('Windows32'))
    else:
        ToolsFolderPath = os.path.join(os.path.abspath(GlobalToolsFolderPath), Path('Windows64'))
elif sys.platform == "linux" or sys.platform == "linux2":
    ToolsFolderPath = os.path.join(os.path.abspath(GlobalToolsFolderPath), Path('Linux'))
    LibFolderPath = os.path.join(os.path.abspath(ToolsFolderPath), Path('lib'))
else:
    ToolsFolderPath = os.path.join(os.path.abspath(GlobalToolsFolderPath), Path('Other Systems'))
AppDataFolderPath = create_app_data_folder()
MergeLogsFolderPath = os.path.join(os.path.abspath(AppDataFolderPath), Path('Logs'))
MediaInfoFolderPath = os.path.join(os.path.abspath(AppDataFolderPath), Path('MediaInfo'))
os.makedirs(MergeLogsFolderPath, exist_ok=True)
os.makedirs(MediaInfoFolderPath, exist_ok=True)
delete_old_media_files()


def get_program_version(program_path, program_name, environment=None):
    try:
        result = subprocess.run(
            [str(program_path), "-V"],
            check=False,
            capture_output=True,
            env=environment or os.environ.copy(),
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    version = result.stdout.strip()
    return version if result.returncode == 0 and program_name in version else ""


def get_custom_program_path(program_name):
    executable_name = program_name + (".exe" if sys.platform == "win32" else "")
    for variable_name in ("MKVTOOLNIX_PATH", "MKVTOOLNIX_DIR"):
        configured_path = os.environ.get(variable_name)
        if not configured_path:
            continue
        candidate = Path(configured_path).expanduser()
        if candidate.is_dir():
            candidate /= executable_name
        if candidate.name.lower() == executable_name.lower():
            return candidate
    return None


def get_program_candidates(program_name):
    executable_name = program_name + (".exe" if sys.platform == "win32" else "")
    candidates = []
    custom_path = get_custom_program_path(program_name)
    if custom_path:
        candidates.append(custom_path)

    system_path = which(program_name)
    if system_path:
        candidates.append(Path(system_path))

    if sys.platform == "win32":
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        candidates.append(program_files / "MKVToolNix" / executable_name)

    candidates.append(Path(ToolsFolderPath) / executable_name)

    unique_candidates = []
    for candidate in candidates:
        candidate = candidate.expanduser()
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)
    return unique_candidates


def get_tool_environment(program_path):
    environment = os.environ.copy()
    portable_tool = Path(program_path).parent == Path(ToolsFolderPath)
    if portable_tool and sys.platform != "win32" and Path(LibFolderPath).is_dir():
        old_library_path = environment.get("LD_LIBRARY_PATH", "")
        environment["LD_LIBRARY_PATH"] = (
            f"{Path(LibFolderPath).absolute()}:{old_library_path}"
        )
    return environment


def resolve_program(program_name):
    for candidate in get_program_candidates(program_name):
        version = get_program_version(
            candidate,
            program_name,
            environment=get_tool_environment(candidate),
        )
        if version:
            logging.info("Using %s: %s", program_name, candidate)
            return str(candidate), version
    logging.warning("Could not find a working %s executable", program_name)
    return program_name, f"{program_name}: not found!"


def get_missing_tools_error():
    missing_tools = []
    if "not found" in MKVMERGE_VERSION:
        missing_tools.append("mkvmerge")
    if "not found" in MKVPROPEDIT_VERSION:
        missing_tools.append("mkvpropedit")
    if not missing_tools:
        return ""
    return (
        "MKVToolNix is required. Could not find: "
        + ", ".join(missing_tools)
        + ". Install MKVToolNix, add it to PATH, or set MKVTOOLNIX_PATH."
    )


def update_enviro_if_not_windows():
    if "LD_LIBRARY_PATH" not in ENVIRONMENT.keys():
        ENVIRONMENT["LD_LIBRARY_PATH"] = ""
    if sys.platform != "win32":
        ENVIRONMENT["LD_LIBRARY_PATH"] = f"{Path(LibFolderPath).absolute()}:{ENVIRONMENT['LD_LIBRARY_PATH']}"


try:
    MyFontPath = os.path.join(os.path.abspath(FontFolderPath), 'OpenSans.ttf')
    WarningCheckBigIconPath = os.path.join(os.path.abspath(IconFolderPath), 'WarningCheckBig.png')
    WarningCheckIconPath = os.path.join(os.path.abspath(IconFolderPath), 'WarningCheck.png')
    TrueCheckIconPath = os.path.join(os.path.abspath(IconFolderPath), 'TrueCheck.png')
    GreenTikMarkIconPath = os.path.join(os.path.abspath(IconFolderPath), 'GreenTikMark.png')
    RedCrossMarkIconPath = os.path.join(os.path.abspath(IconFolderPath), 'RedCrossMark.png')
    ChapterIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Chapter.svg')
    SubtitleLightIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Subtitle_Light.svg')
    AudioLightIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Audio_Light.svg')
    SubtitleDarkIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Subtitle_Dark.svg')
    AudioDarkIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Audio_Dark.svg')
    StartMultiplexingIconPath = os.path.join(os.path.abspath(IconFolderPath), 'StartMultiplexing.png')
    PauseMultiplexingIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Pause.png')
    AddToQueueIconPath = os.path.join(os.path.abspath(IconFolderPath), 'AddToQueue.svg')
    InfoSettingIconPath = os.path.join(os.path.abspath(IconFolderPath), 'InfoSetting.svg')
    InfoIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Info.svg')
    AboutIconPath = os.path.join(os.path.abspath(IconFolderPath), 'About.svg')
    NoMarkIconPath = os.path.join(os.path.abspath(IconFolderPath), 'NoMark.svg')
    RedDashIconPath = os.path.join(os.path.abspath(IconFolderPath), 'RedDash.svg')
    PlusIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Plus.svg')
    TrashLightIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Trash_Light.svg')
    TrashDarkIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Trash_Dark.svg')
    RenameIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Rename.png')
    SwitchIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Switch.svg')
    QuestionIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Question.svg')
    InfoBigIconPath = os.path.join(os.path.abspath(IconFolderPath), 'InfoBig.png')
    OkIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Ok.png')
    PresetLightIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Preset_Light.png')
    PresetDarkIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Preset_Dark.png')
    SelectedItemIconPath = os.path.join(os.path.abspath(IconFolderPath), 'SelectedItemIcon.png')
    UnSelectedItemIconPath = os.path.join(os.path.abspath(IconFolderPath), 'UnSelectedItemIcon.png')
    EmptyIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Empty.png')
    ErrorIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Error.png')
    LeftArrowIconPath = os.path.join(os.path.abspath(IconFolderPath), 'LeftArrow.png')
    RightArrowIconPath = os.path.join(os.path.abspath(IconFolderPath), 'RightArrow.png')
    ErrorBigIconPath = os.path.join(os.path.abspath(IconFolderPath), 'ErrorBig.png')
    DonationsIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Donations.png')
    ClearIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Clear.svg')
    RefreshIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Refresh.png')
    TopLightIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Top_Light.svg')
    DownLightIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Down_Light.svg')
    UpLightIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Up_Light.svg')
    BottomLightIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Bottom_Light.svg')
    TopDarkIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Top_Dark.svg')
    DownDarkIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Down_Dark.svg')
    UpDarkIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Up_Dark.svg')
    BottomDarkIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Bottom_Dark.svg')
    FolderIconPath = os.path.join(os.path.abspath(IconFolderPath), 'SelectFolder.svg')
    SpinnerIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Spinner.gif')
    GoodJobIconPath = os.path.join(os.path.abspath(IconFolderPath), 'GoodJob.png')
    SettingIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Setting.svg')
    TelegramIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Telegram.svg')
    TwitterIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Twitter.svg')
    ThemeIconPath = os.path.join(os.path.abspath(IconFolderPath), 'Day_And_Night.png')
    AppIconPath = os.path.join(os.path.abspath(IconFolderPath), 'App.ico')
    LanguagesFilePath = os.path.join(os.path.abspath(LanguagesFolderPath), "iso639_language_list.json")
    AppLogFilePath = os.path.join(os.path.abspath(AppDataFolderPath), "app_log.txt")
    MuxingLogFilePath = os.path.join(os.path.abspath(AppDataFolderPath), "muxing_log_file.txt")
    TestMkvmergeFilePath = os.path.join(os.path.abspath(AppDataFolderPath), "test_mkvmerge.txt")
    TestMkvpropeditFilePath = os.path.join(os.path.abspath(AppDataFolderPath), "test_mkvpropedit.txt")
    mkvpropeditJsonJobFilePath = os.path.join(os.path.abspath(AppDataFolderPath), "mkvpropeditJob.json")
    mkvmergeJsonJobFilePath = os.path.join(os.path.abspath(AppDataFolderPath), "MkvmergeJob.json")
    mkvmergeJsonInfoFilePath = os.path.join(os.path.abspath(AppDataFolderPath), "MkvmergeInfo.json")
    SettingJsonInfoFilePath = os.path.join(os.path.abspath(AppDataFolderPath), "setting.json")
    QueueSessionFilePath = os.path.join(os.path.abspath(AppDataFolderPath), "queue_session.json")
    TaskBarLibFilePath = os.path.join(os.path.abspath(DLLFolderPath), "TaskbarLib.tlb")
    MKVMERGE_PATH, MKVMERGE_VERSION = resolve_program("mkvmerge")
    MKVPROPEDIT_PATH, MKVPROPEDIT_VERSION = resolve_program("mkvpropedit")
    ENVIRONMENT = get_tool_environment(MKVMERGE_PATH)
except Exception as e:
    logging.error(e)
    raise RuntimeError(f"Failed to initialize application resources: {e}") from e
