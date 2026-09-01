from prompts.prompt_types import Stack
from costs.prompt_compressor import truncate_skeleton


def build_selected_stack_policy(stack: Stack) -> str:
    return f"Selected stack: {stack}."


def build_user_image_policy(image_generation_enabled: bool) -> str:
    if image_generation_enabled:
        return (
            "Image generation is enabled for this request. Use generate_images for "
            "missing assets when needed."
        )

    return (
        "Image generation is disabled for this request. Do not call generate_images. "
        "Use provided media, CSS effects, or placeholder URLs (https://placehold.co)."
    )


def build_adb_data_policy(theme_json: str | None, skeleton_json: str | None) -> str:
    """Build ADB data injection block for Android Compose prompt.

    This formats theme.json and skeleton.json data for injection into the
    design_system parameter. The LLM is instructed to use these EXACT values
    rather than approximating from the screenshot alone.

    Args:
        theme_json: JSON string of extracted design tokens (colors, typography, etc.)
        skeleton_json: JSON string of UI hierarchy with bounds and component types.

    Returns:
        Formatted prompt block string, or empty string if both inputs are None/empty.
    """
    if not theme_json and not skeleton_json:
        return ""

    parts: list[str] = ["## ADB Extracted Design Data\n"]
    parts.append(
        "The following data was extracted from the device screenshot using ADB. "
        "USE THESE EXACT values — do not approximate.\n"
    )

    if theme_json:
        parts.append(f"\n### theme.json (design tokens)\n```json\n{theme_json}\n```\n")

    if skeleton_json:
        # T4: Truncate skeleton to cap prompt size (~8K chars ≈ 2K tokens)
        truncated_skeleton = truncate_skeleton(skeleton_json)
        parts.append(
            f"\n### skeleton.json (UI hierarchy + bounds)\n```json\n{truncated_skeleton}\n```\n"
        )
        parts.append("\nKey constraints from skeleton.json:")
        parts.append(
            "- If fill_ratio < 0.5 for an element, set that element's container to transparent."
        )
        parts.append("- Use the exact hex codes from theme.json. Do not guess colors.")
        parts.append("- Use the exact bounds_device coordinates for layout positioning.")
        parts.append("- Match the component_type for each element (e.g., 'switch' → Switch).")
        parts.append('- Honor the "state" field: "on" = checked, "off" = unchecked.')

    return "".join(parts)
