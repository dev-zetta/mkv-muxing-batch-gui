import json
import os
import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from packages.Startup import GlobalFiles
from packages.Tabs.GlobalSetting import GlobalSetting
from packages.Tabs.MuxSetting.Widgets.GetJsonForMkvmergeJob import GetJsonForMkvmergeJob
from packages.Tabs.MuxSetting.Widgets.GetJsonForMkvpropeditJob import (
    GetJsonForMkvpropeditJob,
)
from packages.Tabs.MuxSetting.Widgets.NameTemplate import (
    escape_json_argument,
    render_name_template,
)
from packages.Tabs.MuxSetting.Widgets.SingleJobData import SingleJobData


class NameTemplateTests(unittest.TestCase):
    def test_all_placeholders_are_rendered(self):
        rendered = render_name_template(
            "{stem} | {old} | {index} | {language} | {filename}",
            "Show.S01E02.mkv",
            old_name="Commentary",
            index=2,
            language="eng",
        )
        self.assertEqual(
            rendered,
            "Show.S01E02 | Commentary | 2 | eng | Show.S01E02.mkv",
        )

    def test_unnamed_track_sentinel_is_not_exposed(self):
        self.assertEqual(
            render_name_template("English{old}", "video.mkv", old_name="UnNamedTrackBeBo"),
            "English",
        )

    def test_response_file_text_is_json_escaped(self):
        escaped = escape_json_argument('A "quoted" name\\part')
        self.assertEqual(json.loads(f'"{escaped}"'), 'A "quoted" name\\part')


class NameManipulationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.saved_settings = {
            "video": GlobalSetting.MUX_SETTING_VIDEO_TITLE_TEMPLATE,
            "audio": GlobalSetting.MUX_SETTING_AUDIO_NAME_TEMPLATE,
            "subtitle": GlobalSetting.MUX_SETTING_SUBTITLE_NAME_TEMPLATE,
            "destination": GlobalSetting.DESTINATION_FOLDER_PATH,
            "overwrite": GlobalSetting.OVERWRITE_SOURCE_FILES,
            "subtitle_enabled": GlobalSetting.SUBTITLE_ENABLED,
        }

    def tearDown(self):
        GlobalSetting.MUX_SETTING_VIDEO_TITLE_TEMPLATE = self.saved_settings["video"]
        GlobalSetting.MUX_SETTING_AUDIO_NAME_TEMPLATE = self.saved_settings["audio"]
        GlobalSetting.MUX_SETTING_SUBTITLE_NAME_TEMPLATE = self.saved_settings["subtitle"]
        GlobalSetting.DESTINATION_FOLDER_PATH = self.saved_settings["destination"]
        GlobalSetting.OVERWRITE_SOURCE_FILES = self.saved_settings["overwrite"]
        GlobalSetting.SUBTITLE_ENABLED = self.saved_settings["subtitle_enabled"]

    @staticmethod
    def tool_exists(tool):
        return os.path.isfile(tool) or shutil.which(tool) is not None

    @staticmethod
    def write_test_wave(path):
        with wave.open(str(path), "wb") as audio_file:
            audio_file.setnchannels(1)
            audio_file.setsampwidth(2)
            audio_file.setframerate(8000)
            audio_file.writeframes(b"\x00\x00" * 800)

    @staticmethod
    def inspect_mkv(path):
        output = subprocess.check_output(
            [GlobalFiles.MKVMERGE_PATH, "-J", str(path)],
            env=GlobalFiles.ENVIRONMENT,
            text=True,
            encoding="utf-8",
        )
        return json.loads(output)

    def create_source_mkv(self, folder):
        audio_path = folder / "audio.wav"
        subtitle_path = folder / "subtitle.srt"
        source_path = folder / "source.mkv"
        self.write_test_wave(audio_path)
        subtitle_path.write_text(
            "1\n00:00:00,000 --> 00:00:00,050\nHello\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                GlobalFiles.MKVMERGE_PATH,
                "--output", str(source_path),
                "--title", "Old Title",
                "--language", "0:eng", "--track-name", "0:Old Audio", str(audio_path),
                "--language", "0:spa", "--track-name", "0:Old Subtitle", str(subtitle_path),
            ],
            env=GlobalFiles.ENVIRONMENT,
            check=True,
            capture_output=True,
        )
        return source_path

    def configure_templates(self):
        GlobalSetting.MUX_SETTING_VIDEO_TITLE_TEMPLATE = '"{stem}" Remux'
        GlobalSetting.MUX_SETTING_AUDIO_NAME_TEMPLATE = "{language} {index} - {old}"
        GlobalSetting.MUX_SETTING_SUBTITLE_NAME_TEMPLATE = "{stem} - {old}"

    def assert_metadata_was_renamed(self, path, expected_stem, extra_subtitle_name=None):
        metadata = self.inspect_mkv(path)
        self.assertEqual(
            metadata["container"]["properties"]["title"],
            f'"{expected_stem}" Remux',
        )
        audio_names = [
            track["properties"]["track_name"]
            for track in metadata["tracks"]
            if track["type"] == "audio"
        ]
        subtitle_names = [
            track["properties"]["track_name"]
            for track in metadata["tracks"]
            if track["type"] == "subtitles"
        ]
        self.assertEqual(audio_names, ["eng 1 - Old Audio"])
        self.assertIn(f"{expected_stem} - Old Subtitle", subtitle_names)
        if extra_subtitle_name:
            self.assertIn(extra_subtitle_name, subtitle_names)

    def test_mkvmerge_applies_title_and_existing_track_templates(self):
        if not self.tool_exists(GlobalFiles.MKVMERGE_PATH):
            self.skipTest("mkvmerge is unavailable")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_folder = root / "input"
            output_folder = root / "output"
            source_folder.mkdir()
            output_folder.mkdir()
            source_path = self.create_source_mkv(source_folder)
            new_subtitle_path = source_folder / "new-subtitle.srt"
            new_subtitle_path.write_text(
                "1\n00:00:00,000 --> 00:00:00,050\nNew subtitle\n",
                encoding="utf-8",
            )
            response_path = root / "mkvmerge.json"

            old_response_path = GlobalFiles.mkvmergeJsonJobFilePath
            try:
                GlobalFiles.mkvmergeJsonJobFilePath = str(response_path)
                GlobalSetting.DESTINATION_FOLDER_PATH = str(output_folder)
                GlobalSetting.OVERWRITE_SOURCE_FILES = False
                self.configure_templates()

                job = SingleJobData()
                job.video_name = source_path.name
                job.video_name_absolute = str(source_path)
                job.subtitle_found = True
                job.subtitle_name_absolute = [str(new_subtitle_path)]
                job.subtitle_track_name = ["New Added"]
                job.subtitle_language = ["Spanish"]
                job.subtitle_set_default = [False]
                job.subtitle_set_forced = [False]
                job.subtitle_delay = [0.0]
                job.subtitle_set_at_top = [-1]
                GlobalSetting.SUBTITLE_ENABLED = True
                GetJsonForMkvmergeJob(job)
                subprocess.run(
                    [GlobalFiles.MKVMERGE_PATH, f"@{response_path}"],
                    env=GlobalFiles.ENVIRONMENT,
                    check=True,
                    capture_output=True,
                )
                self.assert_metadata_was_renamed(
                    output_folder / source_path.name,
                    "source",
                    extra_subtitle_name="source - New Added",
                )
            finally:
                GlobalFiles.mkvmergeJsonJobFilePath = old_response_path

    def test_mkvpropedit_applies_title_and_existing_track_templates(self):
        if not self.tool_exists(GlobalFiles.MKVMERGE_PATH) or not self.tool_exists(GlobalFiles.MKVPROPEDIT_PATH):
            self.skipTest("MKVToolNix is unavailable")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = self.create_source_mkv(root)
            edited_path = root / "edited.mkv"
            shutil.copy2(source_path, edited_path)
            response_path = root / "mkvpropedit.json"

            old_response_path = GlobalFiles.mkvpropeditJsonJobFilePath
            try:
                GlobalFiles.mkvpropeditJsonJobFilePath = str(response_path)
                self.configure_templates()

                job = SingleJobData()
                job.video_name = edited_path.name
                job.video_name_absolute = str(edited_path)
                GetJsonForMkvpropeditJob(job)
                subprocess.run(
                    [GlobalFiles.MKVPROPEDIT_PATH, f"@{response_path}"],
                    env=GlobalFiles.ENVIRONMENT,
                    check=True,
                    capture_output=True,
                )
                self.assert_metadata_was_renamed(edited_path, "edited")
            finally:
                GlobalFiles.mkvpropeditJsonJobFilePath = old_response_path


if __name__ == "__main__":
    unittest.main()
