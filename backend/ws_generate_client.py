"""
WebSocket client for screenshot-to-code backend.

Connects to the backend's /generate-code WebSocket endpoint, sends the
exact same JSON payload the frontend sends, and collects the Agent's
streamed output. This gives scripts the full Agent pipeline (tool-calling,
multi-turn editing, budget control, screenshot preview) for free.

Usage:
  # Set API keys (at least one required)
  export OPENAI_API_KEY=sk-xxx          # or ANTHROPIC_API_KEY / GEMINI_API_KEY
  export OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3  # for doubao

  # Run the client
  python ws_generate_client.py \\
    --screenshot e2e_demo/screenshots/run_20260901/source_screenshot.png \\
    --stack html_tailwind \\
    --output e2e_demo/run_20260901/ws_output.html

  # For Android Compose (requires ADB data injection)
  python ws_generate_client.py \\
    --screenshot e2e_demo/screenshots/run_20260901/source_screenshot.png \\
    --stack android_compose \\
    --design-system-file e2e_demo/run_20260901/design_system_block.txt \\
    --output e2e_demo/run_20260901/ws_compose.kt

  # Specify model (optional, auto-selected by backend if omitted)
  python ws_generate_client.py \\
    --screenshot screenshot.png \\
    --stack html_tailwind \\
    --model doubao-seed-2.1-turbo \\
    --output output.html

Requirements:
  pip install websockets Pillow
"""
import argparse
import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path

import websockets

BACKEND_WS_URL = os.environ.get("WS_BACKEND_URL", "ws://127.0.0.1:7001")


def image_to_data_url(image_path: str, max_width: int = 768, quality: int = 85) -> str:
    """Convert an image file to a JPEG data URL, optionally resized."""
    from PIL import Image
    import io

    img = Image.open(image_path)
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"


def build_params(
    screenshot_data_url: str,
    stack: str,
    openai_api_key: str | None,
    anthropic_api_key: str | None,
    gemini_api_key: str | None,
    openai_base_url: str | None,
    model: str | None = None,
    design_system: str | None = None,
    text_prompt: str = "",
    num_variants: int = 1,
) -> dict:
    """Build the FullGenerationSettings JSON payload, matching frontend format.

    This is the exact structure the frontend sends via WebSocket.send().
    See: frontend/src/types.ts FullGenerationSettings
    """
    params = {
        # CodeGenerationParams
        "generationType": "create",
        "inputMode": "image",
        "prompt": {
            "text": text_prompt or "Generate code that looks exactly like the screenshot.",
            "images": [screenshot_data_url],
        },
        "history": [],
        "isAssetExtractionEnabled": False,
        # Settings (API keys — passed same as frontend settings dialog)
        "openAiApiKey": openai_api_key,
        "anthropicApiKey": anthropic_api_key,
        "geminiApiKey": gemini_api_key,
        "openAiBaseURL": openai_base_url,
        "replicateApiKey": None,
        "isImageGenerationEnabled": False,
        # Stack selection
        "generatedCodeConfig": stack,
        # Design system (ADB data injection)
        "designSystem": design_system,
    }

    return params


async def generate_via_websocket(
    params: dict,
    ws_url: str = BACKEND_WS_URL,
    output_path: str = "output.html",
    verbose: bool = True,
) -> dict:
    """Connect to backend WebSocket, send params, collect all output.

    Returns a dict with:
        - code: final generated code (str)
        - variants: list of per-variant results
        - errors: list of error messages
        - raw_messages: all WebSocket messages for debugging
    """
    url = f"{ws_url}/generate-code"
    if verbose:
        print(f"Connecting to {url} ...")

    result = {
        "code": "",
        "variants": {},
        "errors": [],
        "raw_messages": [],
        "variant_count": 0,
        "variant_models": [],
    }

    t0 = time.time()

    async with websockets.connect(url) as ws:
        # Send the full generation params (same as frontend ws.send)
        await ws.send(json.dumps(params))
        if verbose:
            print(f"Sent params (stack={params.get('generatedCodeConfig')})")
            print(f"  image in prompt: {bool(params.get('prompt', {}).get('images'))}")
            print()

        # Collect messages until connection closes
        while True:
            try:
                raw = await ws.recv()
            except websockets.exceptions.ConnectionClosed as e:
                if verbose:
                    elapsed = time.time() - t0
                    print(f"\nConnection closed (code={e.code}, {elapsed:.1f}s)")
                break

            msg = json.loads(raw)
            msg_type = msg.get("type")
            variant_idx = msg.get("variantIndex", 0)
            result["raw_messages"].append(msg)

            if msg_type == "variantCount":
                count = int(msg.get("value", 1))
                result["variant_count"] = count
                if verbose:
                    print(f"[variantCount] {count} variants")

            elif msg_type == "variantModels":
                models = msg.get("data", {}).get("models", [])
                result["variant_models"] = models
                if verbose:
                    print(f"[variantModels] {models}")

            elif msg_type == "status":
                value = msg.get("value", "")
                if verbose:
                    print(f"[status] v{variant_idx+1}: {value}")

            elif msg_type == "setCode":
                code = msg.get("value", "")
                result["variants"].setdefault(variant_idx, {})["code"] = code
                if verbose:
                    print(f"[setCode] v{variant_idx+1}: {len(code)} chars")

            elif msg_type == "chunk":
                chunk = msg.get("value", "")
                if verbose:
                    print(f"[chunk] v{variant_idx+1}: +{len(chunk)} chars")

            elif msg_type == "thinking":
                text = msg.get("value", "")
                if verbose:
                    snippet = text[:80].replace("\n", " ")
                    print(f"[thinking] v{variant_idx+1}: {snippet}...")

            elif msg_type == "assistant":
                text = msg.get("value", "")
                if verbose:
                    snippet = text[:80].replace("\n", " ")
                    print(f"[assistant] v{variant_idx+1}: {snippet}")

            elif msg_type == "toolStart":
                data = msg.get("data", {})
                tool_name = data.get("name", "?")
                if verbose:
                    print(f"[toolStart] v{variant_idx+1}: {tool_name}")

            elif msg_type == "toolResult":
                data = msg.get("data", {})
                ok = data.get("ok", False)
                if verbose:
                    print(f"[toolResult] v{variant_idx+1}: {tool_name if 'tool_name' in data else ''} ok={ok}")

            elif msg_type == "variantComplete":
                if verbose:
                    print(f"[variantComplete] v{variant_idx+1}")

            elif msg_type == "variantError":
                error = msg.get("value", "Unknown error")
                result["errors"].append({"variant": variant_idx, "error": error})
                if verbose:
                    print(f"[variantError] v{variant_idx+1}: {error}")

            elif msg_type == "error":
                error = msg.get("value", "Unknown error")
                result["errors"].append({"variant": -1, "error": error})
                if verbose:
                    print(f"[ERROR] {error}")

    # Pick the first variant's code as primary output
    if result["variants"]:
        first_idx = min(result["variants"].keys())
        result["code"] = result["variants"][first_idx].get("code", "")

    # Write output file
    if result["code"] and output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result["code"])
        if verbose:
            print(f"\nOutput written to {output_path} ({len(result['code'])} chars)")

    # Summary
    if verbose:
        elapsed = time.time() - t0
        print(f"\n{'='*60}")
        print(f"SUMMARY ({elapsed:.1f}s)")
        print(f"{'='*60}")
        print(f"  Variants: {result['variant_count']}")
        print(f"  Models: {result['variant_models']}")
        print(f"  Successful: {len(result['variants'])}")
        print(f"  Errors: {len(result['errors'])}")
        for vidx, vdata in sorted(result["variants"].items()):
            code_len = len(vdata.get("code", ""))
            print(f"    v{vidx+1}: {code_len} chars")
        if result["errors"]:
            for err in result["errors"]:
                print(f"    v{err['variant']+1 if err['variant']>=0 else 'global'}: {err['error'][:100]}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate code via backend WebSocket (full Agent pipeline)"
    )
    parser.add_argument(
        "--screenshot", required=True,
        help="Path to the screenshot image file"
    )
    parser.add_argument(
        "--stack", default="html_tailwind",
        help="Code stack: html_tailwind, html_css, react_tailwind, bootstrap, vue_tailwind, ionic_tailwind, or android_compose"
    )
    parser.add_argument(
        "--output", "-o", default="output.html",
        help="Output file path"
    )
    parser.add_argument(
        "--model", default=None,
        help="Model to use (auto-selected by backend if omitted). Example: doubao-seed-2.1-turbo"
    )
    parser.add_argument(
        "--design-system-file", default=None,
        help="Path to a file containing the design system block (ADB theme+skeleton)"
    )
    parser.add_argument(
        "--prompt", default="",
        help="Additional text prompt"
    )
    parser.add_argument(
        "--ws-url", default=None,
        help=f"Backend WebSocket URL (default: {BACKEND_WS_URL})"
    )
    parser.add_argument(
        "--max-width", type=int, default=768,
        help="Max image width for compression (default: 768)"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress verbose output"
    )
    args = parser.parse_args()

    # Read API keys from environment
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    openai_base_url = os.environ.get("OPENAI_BASE_URL")

    if not openai_api_key and not anthropic_api_key and not gemini_api_key:
        print("ERROR: At least one API key required.")
        print("  Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY")
        sys.exit(1)

    # Convert screenshot to data URL
    if not Path(args.screenshot).exists():
        print(f"ERROR: Screenshot not found: {args.screenshot}")
        sys.exit(1)

    screenshot_data_url = image_to_data_url(args.screenshot, max_width=args.max_width)
    print(f"Screenshot: {args.screenshot} → {len(screenshot_data_url)} chars (JPEG data URL)")

    # Read design system block if provided
    design_system = None
    if args.design_system_file:
        with open(args.design_system_file, "r", encoding="utf-8") as f:
            design_system = f.read()

    # Build params (exact same format as frontend)
    params = build_params(
        screenshot_data_url=screenshot_data_url,
        stack=args.stack,
        openai_api_key=openai_api_key,
        anthropic_api_key=anthropic_api_key,
        gemini_api_key=gemini_api_key,
        openai_base_url=openai_base_url,
        model=args.model,
        design_system=design_system,
        text_prompt=args.prompt,
    )

    ws_url = args.ws_url or BACKEND_WS_URL

    # Run
    result = asyncio.run(generate_via_websocket(
        params=params,
        ws_url=ws_url,
        output_path=args.output,
        verbose=not args.quiet,
    ))

    # Exit code: 0 if at least one variant succeeded, 1 otherwise
    sys.exit(0 if result["variants"] else 1)


if __name__ == "__main__":
    main()
