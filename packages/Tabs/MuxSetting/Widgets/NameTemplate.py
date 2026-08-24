import json
from pathlib import Path

UNNAMED_TRACK_SENTINEL = "UnNamedTrackBeBo"


def normalize_old_name(name):
    if name in (None, UNNAMED_TRACK_SENTINEL):
        return ""
    return str(name)


def render_name_template(template, file_name, old_name="", index=1, language=""):
    """Render a deliberately small, predictable metadata-name template."""
    file_path = Path(str(file_name))
    replacements = {
        "{old}": normalize_old_name(old_name),
        "{filename}": file_path.name,
        "{stem}": file_path.stem,
        "{index}": str(index),
        "{language}": str(language),
    }
    result = str(template)
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


def escape_json_argument(value):
    """Escape text that will be wrapped by the legacy response-file writer."""
    return json.dumps(str(value), ensure_ascii=False)[1:-1]
