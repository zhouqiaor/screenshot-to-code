"""
Try to create a preset inference endpoint for doubao-seed-1-6-vision-250815
using the volcengine SDK with IAM Access Key authentication.

Note: CreateEndpoint API requires IAM Access Key authentication,
NOT the Ark API Key (Bearer token). We need to check if the user has IAM credentials.
"""
import sys
sys.path.insert(0, r'C:\Users\georgeslark\.workbuddy\binaries\python\envs\default\Lib\site-packages')

import os

# Check if IAM Access Keys are available in environment
access_key = os.environ.get("VOLCENGINE_ACCESS_KEY", "")
secret_key = os.environ.get("VOLCENGINE_SECRET_KEY", "")

if not access_key or not secret_key:
    print("=" * 70)
    print("ERROR: IAM Access Key not found in environment!")
    print("=" * 70)
    print()
    print("CreateEndpoint API requires IAM Access Key authentication,")
    print("NOT the Ark API Key (Bearer token).")
    print()
    print("To use this API, you need:")
    print("  1. Go to: https://console.volcengine.com/iam/keymanage/")
    print("  2. Create or view your Access Key ID and Secret Access Key")
    print("  3. Set environment variables:")
    print('     export VOLCENGINE_ACCESS_KEY="AK..."')
    print('     export VOLCENGINE_SECRET_KEY="SK..."')
    print()
    print("Alternative solution (no IAM needed):")
    print("  1. Go to: https://console.volcengine.com/ark/region:ark+cn-beijing/experience-center")
    print("  2. Select model: doubao-seed-1.6-vision")
    print("  3. Send any message in the chat (e.g., '你好')")
    print("  4. This auto-creates a preset inference endpoint")
    print("  5. Then use model ID 'doubao-seed-1-6-vision-250815' directly in API calls")
    sys.exit(1)

print(f"Access Key found: {access_key[:10]}...")
print(f"Secret Key found: {secret_key[:10]}...")

try:
    import volcenginesdkark
    from volcenginesdkcore import Credentials

    # Initialize the Ark API client with IAM credentials
    credentials = Credentials(access_key, secret_key, 'ark', 'cn-beijing')
    ark_service = volcenginesdkark.ARKApi(credentials)

    # Try to create an endpoint for doubao-seed-1-6-vision-250815
    # The model name and version need to be separated
    # Name: doubao-seed-1-6-vision, ModelVersion: 250815
    create_endpoint_request = {
        "Name": "doubao-seed-1-6-vision-endpoint",
        "Description": "Preset endpoint for doubao-seed-1.6-vision model",
        "ModelReference": {
            "FoundationModel": {
                "Name": "doubao-seed-1-6-vision",
                "ModelVersion": "250815"
            }
        },
        "DryRun": False
    }

    print("\nAttempting to create endpoint...")
    print(f"Request: {create_endpoint_request}")

    result = ark_service.create_endpoint(create_endpoint_request)
    print(f"\nResult: {result}")
    print(f"Endpoint ID: {result.Id if hasattr(result, 'Id') else 'unknown'}")

except ImportError as e:
    print(f"SDK import error: {e}")
    print("Trying alternative approach with raw HTTP + IAM signature...")

    # Alternative: Use raw HTTP with V4 signature
    # This is complex but doesn't require the SDK
    import hashlib
    import hmac
    import time
    import httpx
    from datetime import datetime

    # V4 signature for Volcengine API
    service = "ark"
    region = "cn-beijing"
    host = "ark.cn-beijing.volcengineapi.com"
    endpoint = f"https://{host}"

    def sign_v4(method, path, query, headers, body, ak, sk, service, region):
        """Generate V4 signature for Volcengine API."""
        # 1. Create canonical request
        content_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()

        now = datetime.utcnow()
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        headers_for_sign = {
            "Content-Type": "application/json",
            "Host": host,
            "X-Date": amz_date,
        }

        signed_headers = sorted(headers_for_sign.keys())
        canonical_headers = "\n".join(
            f"{k}:{headers_for_sign[k]}" for k in signed_headers
        )

        canonical_request = (
            f"{method}\n{path}\n{query}\n{canonical_headers}\n\n"
            f"{';'.join(signed_headers)}\n{content_sha256}"
        )

        # 2. Create string to sign
        scope = f"{date_stamp}/{region}/{service}/request"
        string_to_sign = f"HMAC-SHA256\n{amz_date}\n{scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"

        # 3. Calculate signature
        k_date = hmac.new(("VOLCENGINE" + sk).encode("utf-8"), date_stamp.encode("utf-8"), hashlib.sha256).digest()
        k_region = hmac.new(k_date, region.encode("utf-8"), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service.encode("utf-8"), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, "request".encode("utf-8"), hashlib.sha256).digest()
        signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        # 4. Create authorization header
        authorization = (
            f"HMAC-SHA256 Credential={ak}/{scope}, "
            f"SignedHeaders={';'.join(signed_headers)}, "
            f"Signature={signature}"
        )

        headers_for_sign["Authorization"] = authorization
        return headers_for_sign

    body_json = json.dumps({
        "Name": "doubao-seed-1-6-vision-endpoint",
        "Description": "Preset endpoint for doubao-seed-1.6-vision model",
        "ModelReference": {
            "FoundationModel": {
                "Name": "doubao-seed-1-6-vision",
                "ModelVersion": "250815"
            }
        },
        "DryRun": False
    })

    path = "/"
    query = "Action=CreateEndpoint&Version=2024-01-01"
    method = "POST"

    print("\nAttempting with V4 signed request...")
    signed_headers = sign_v4(method, path, query, {}, body_json, access_key, secret_key, service, region)

    client = httpx.Client(timeout=30.0)
    url = f"{endpoint}/?{query}"
    resp = client.post(url, headers=signed_headers, content=body_json)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:500]}")
    client.close()
