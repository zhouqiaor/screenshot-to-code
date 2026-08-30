from dataclasses import dataclass, field
from typing import Any, Dict, List

from openai.types.chat import ChatCompletionMessageParam

from codegen.utils import extract_html_content


@dataclass
class AgentFileState:
    """Multi-file state model.

    For web stacks, ``files`` contains a single entry and ``active_path``
    points to it — behaviour is identical to the old single-file model.

    For Android Compose, the LLM creates multiple files (``MainActivity.kt``
    and ``preview.html``) via successive ``create_file`` calls.  Each call
    adds a key to ``files`` and sets ``active_path`` to the new path, so
    no file is overwritten.
    """

    files: Dict[str, str] = field(default_factory=lambda: {"index.html": ""})
    active_path: str = "index.html"

    # ------------------------------------------------------------------
    # Backward-compatible property accessors
    # ------------------------------------------------------------------
    @property
    def path(self) -> str:
        """Active file path (read-only — use ``set_file`` to change)."""
        return self.active_path

    @path.setter
    def path(self, value: str) -> None:
        """Migrate legacy direct ``.path = …`` assignments to ``set_file``."""
        if value and value not in self.files:
            self.files[value] = ""
        self.active_path = value

    @property
    def content(self) -> str:
        """Content of the active file."""
        return self.files.get(self.active_path, "")

    @content.setter
    def content(self, value: str) -> None:
        """Set content of the active file (no overwrite of other files)."""
        self.files[self.active_path] = value

    # ------------------------------------------------------------------
    # Multi-file operations
    # ------------------------------------------------------------------
    def set_file(self, path: str, content: str) -> None:
        """Create or replace a single file and make it the active one."""
        self.files[path] = content
        self.active_path = path
        # Remove stale default entry if it was never explicitly written to.
        default_key = "index.html"
        if path != default_key and self.files.get(default_key) == "":
            del self.files[default_key]

    def get_file(self, path: str) -> str:
        """Return content of a specific file (empty string if missing)."""
        return self.files.get(path, "")

    def list_paths(self) -> List[str]:
        """All file paths currently tracked, in insertion order."""
        return list(self.files.keys())

    @staticmethod
    def default_path_for_stack(stack: str) -> str:
        """Return the default file path for a given stack."""
        if stack == "android_compose":
            return "MainActivity.kt"
        return "index.html"


def ensure_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def extract_text_content(message: ChatCompletionMessageParam) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                return ensure_str(part.get("text"))
    return ""


def seed_file_state_from_messages(
    file_state: AgentFileState,
    prompt_messages: List[ChatCompletionMessageParam],
    stack: str = "",
) -> None:
    if file_state.content:
        return

    default_path = AgentFileState.default_path_for_stack(stack)

    for message in reversed(prompt_messages):
        if message.get("role") != "assistant":
            continue
        raw_text = extract_text_content(message)
        if not raw_text:
            continue
        extracted = extract_html_content(raw_text, stack=stack)
        content = extracted or raw_text
        file_state.set_file(default_path, content)
        return

    if not prompt_messages:
        return

    system_message = prompt_messages[0]
    if system_message.get("role") != "system":
        return

    system_text = extract_text_content(system_message)
    markers = [
        "Here is the code of the app:",
    ]
    for marker in markers:
        if marker not in system_text:
            continue
        raw_text = system_text.split(marker, 1)[1].strip()
        extracted = extract_html_content(raw_text, stack=stack)
        content = extracted or raw_text
        file_state.set_file(default_path, content)
        return
