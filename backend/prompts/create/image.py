from openai.types.chat import ChatCompletionContentPartParam, ChatCompletionMessageParam

from prompts.prompt_types import Stack
from prompts import system_prompt
from prompts.android_compose_system import ANDROID_COMPOSE_SYSTEM_PROMPT
from prompts.design_system import build_design_system_prompt_block
from prompts.policies import build_selected_stack_policy, build_user_image_policy

def build_image_prompt_messages(
    image_data_urls: list[str],
    stack: Stack,
    text_prompt: str,
    image_generation_enabled: bool,
    design_system: str | None = None,
) -> list[ChatCompletionMessageParam]:
    image_policy = build_user_image_policy(image_generation_enabled)
    selected_stack = build_selected_stack_policy(stack)
    design_system_block = build_design_system_prompt_block(design_system)

    # Build target-specific instructions based on stack
    if stack == "android_compose":
        target_instructions = f"""
Generate Kotlin code using Jetpack Compose (Material 3) that looks exactly like the provided screenshot(s).

{selected_stack}
{design_system_block}

## Replication instructions

- Output ONLY valid Kotlin code in a single file. No explanations, no markdown fences.
- The Kotlin file should define a @Composable function that renders the entire UI.
- Use Jetpack Compose Material 3 components (Surface, Text, Switch, Slider, Icon, etc.).
- Use the exact text from the screenshot.
- Match the layout structure: Column, Row, Spacer, Surface, etc.
- Use appropriate Material 3 colors and typography.
- If the screenshot shows a settings page, include all settings items (toggles, sliders, etc.).
- Import statements should be at the top of the file.
- Do NOT wrap output in markdown code fences.

- {image_policy}
"""
    else:
        target_instructions = f"""
Generate code for a web page that looks exactly like the provided screenshot(s).

{selected_stack}
{design_system_block}

## Replication instructions

- Make sure the web page looks exactly like the screenshot.
- Use the exact text from the screenshot.
- Since our goal is to make the web page look as close to the screenshot as possible, we need to extract the exact image assets where possible and generate images for the assets that are not extractable.
- Extracting assets can be done with the extract_assets tool. After extracting assets, make sure to inspect the extracted image closely to ensure that it is what we want.
- When available, use edit_images for asset edits such as removing unwanted elements, batching independent edits into one call.
- If an extracted or supplied asset is visibly low-resolution or pixelated and must render larger, upscale it with edit_images—not CSS stretching or generate_images.
- If an asset in the original screenshot is not extractable (for example, occluded by other objects or is the background), when available, use generate_images to create image URLs from prompts (you may pass multiple prompts).

- {image_policy}

## Multiple screenshots

If multiple screenshots are provided, organize them meaningfully:

- If they appear to be different pages in a website, make them distinct pages and link them.
- If they look like different tabs or views in an app, connect them with appropriate navigation.
- If they appear unrelated, create a scaffold that separates them into "Screenshot 1", "Screenshot 2", "Screenshot 3", etc. so it is easy to navigate.
- For mobile screenshots, do not include the device frame or browser chrome; focus only on the actual UI mockups.
"""
    user_prompt = target_instructions

    # Add additional instructions provided by the user
    if text_prompt.strip():
        user_prompt = f"{user_prompt}\n\nAdditional instructions: {text_prompt}"

    user_content: list[ChatCompletionContentPartParam] = []
    for image_data_url in image_data_urls:
        user_content.append(
            {
                "type": "image_url",
                "image_url": {"url": image_data_url, "detail": "high"},
            }
        )
    user_content.append(
        {
            "type": "text",
            "text": user_prompt,
        }
    )
    return [
        {
            "role": "system",
            "content": ANDROID_COMPOSE_SYSTEM_PROMPT if stack == "android_compose" else system_prompt.SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]
