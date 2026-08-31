"""Stack-based model routing (R2.1).

Routes model selection based on the target stack when the user has not
explicitly chosen a model.  Simple stacks get cheaper models; complex
stacks get higher-quality models.

Design ref: design-docs/token-governance-design.md §3.3 R2.1
"""

from __future__ import annotations

from typing import Optional

from llm import Llm

# Default model preference per stack (when user does not explicitly choose).
# Rationale:
# - Web stacks with Tailwind/React → high thinking (complex layouts)
# - Bootstrap/HTML/CSS → medium thinking (simpler styling)
# - Android Compose → low thinking (structured, less ambiguity)
# - Unknown stacks → high thinking (safe default)
STACK_MODEL_PREFERENCE: dict[str, Llm] = {
    # High-complexity stacks
    "html_tailwind": Llm.GEMINI_3_6_FLASH_HIGH,
    "react_tailwind": Llm.GEMINI_3_6_FLASH_HIGH,
    # Medium-complexity stacks
    "bootstrap": Llm.GEMINI_3_6_FLASH_LOW,
    "html_css": Llm.GEMINI_3_6_FLASH_LOW,
    "vue_tailwind": Llm.GEMINI_3_6_FLASH_LOW,
    "ionic_tailwind": Llm.GEMINI_3_6_FLASH_LOW,
    # Low-complexity / structured stacks (cheapest viable)
    "android_compose": Llm.GEMINI_3_6_FLASH_MINIMAL,
}

_DEFAULT_MODEL = Llm.GEMINI_3_6_FLASH_HIGH


def route_model(stack: str, user_model: Optional[Llm] = None) -> Llm:
    """Select a model for the given stack.

    User's explicit choice always takes precedence.  When no model is
    chosen, fall back to the stack preference table, then to the default.
    """
    if user_model is not None:
        return user_model
    return STACK_MODEL_PREFERENCE.get(stack, _DEFAULT_MODEL)
