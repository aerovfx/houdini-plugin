"""Pixibox API client for Houdini."""

import json
import urllib.request
import urllib.error
import os
from typing import Optional, Tuple


class PixiboxAPI:
    """API client for Pixibox.ai services in Houdini."""

    BASE_URL = "https://pixibox.ai/api/v1"
    TIMEOUT = 30

    def __init__(self, api_key: str):
        """Initialize API client with API key.

        Args:
            api_key: Bearer token starting with 'px_live_'
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Houdini-Pixibox-Plugin/1.0",
        }

    def generate(
        self, input_type: str, input_data: str, model: str
    ) -> Tuple[bool, Optional[str], str]:
        """Start a 3D generation request.

        Args:
            input_type: 'image_to_3d' or 'text_to_3d'
            input_data: File path (for image) or text prompt
            model: AI model name

        Returns:
            Tuple of (success, generation_id, message)
        """
        try:
            # Map input type to correct format
            if input_type in ("image", "image_to_3d"):
                success, image_data, msg = self.upload_image(input_data)
                if not success:
                    return False, None, f"Image upload failed: {msg}"
                payload = {
                    "type": "image_to_3d",
                    "input": image_data,
                    "model": model,
                }
            elif input_type in ("text", "text_to_3d"):
                payload = {
                    "type": "text_to_3d",
                    "input": input_data,
                    "model": model,
                }
            else:
                return False, None, "Invalid input type (use 'image_to_3d' or 'text_to_3d')"

            req = urllib.request.Request(
                f"{self.BASE_URL}/generate",
                method="POST",
                headers=self.headers,
                data=json.dumps(payload).encode("utf-8"),
            )

            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
                generation_id = data.get("id")
                return True, generation_id, "Generation started"

        except urllib.error.HTTPError as e:
            error_msg = e.read().decode("utf-8")
            return False, None, f"HTTP {e.code}: {error_msg}"
        except Exception as e:
            return False, None, str(e)

    def check_status(self, generation_id: str) -> Tuple[str, Optional[str], str]:
        """Check generation status.

        Args:
            generation_id: ID returned from generate()

        Returns:
            Tuple of (status, model_url, message)
        """
        try:
            req = urllib.request.Request(
                f"{self.BASE_URL}/generations/{generation_id}",
                method="GET",
                headers=self.headers,
            )

            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
                status = data.get("status", "unknown")
                model_url = data.get("modelUrl")
                message = data.get("errorMessage", "")
                return status, model_url, message

        except Exception as e:
            return "error", None, str(e)

    def download_model(self, url: str, filepath: str) -> Tuple[bool, str]:
        """Download 3D model from URL (GCS signed URL or direct download).

        Args:
            url: Download URL (GCS signed URL or direct public URL)
            filepath: Local file path to save to

        Returns:
            Tuple of (success, message)
        """
        try:
            # GCS signed URLs don't need auth header
            if "storage.googleapis.com" in url or url.startswith("https://"):
                req = urllib.request.Request(url)
            else:
                req = urllib.request.Request(url, headers=self.headers)

            with urllib.request.urlopen(req, timeout=60) as response:
                with open(filepath, "wb") as f:
                    f.write(response.read())
            return True, f"Downloaded to {filepath}"
        except Exception as e:
            return False, str(e)

    def upload_image(self, filepath: str) -> Tuple[bool, Optional[str], str]:
        """Upload image to Pixibox.

        Args:
            filepath: Local image file path

        Returns:
            Tuple of (success, image_data_or_url, message)
        """
        try:
            if not os.path.exists(filepath):
                return False, None, "File not found"

            with open(filepath, "rb") as f:
                image_data = f.read()

            boundary = "----PixiboxFormBoundary"
            body = []
            body.append(f"--{boundary}".encode())
            body.append(
                b'Content-Disposition: form-data; name="image"; filename="image.png"'
            )
            body.append(b"Content-Type: image/png")
            body.append(b"")
            body.append(image_data)
            body.append(f"--{boundary}--".encode())
            body.append(b"")

            body_bytes = b"\r\n".join(body)

            headers = dict(self.headers)
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"

            req = urllib.request.Request(
                f"{self.BASE_URL}/upload",
                method="POST",
                headers=headers,
                data=body_bytes,
            )

            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
                image_url = data.get("url")
                return True, image_url, "Image uploaded"

        except Exception as e:
            return False, None, str(e)

    def validate_api_key(self) -> Tuple[bool, str]:
        """Validate API key.

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            req = urllib.request.Request(
                f"{self.BASE_URL}/auth/validate",
                method="GET",
                headers=self.headers,
            )

            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
                if data.get("valid"):
                    return True, "Valid"
                else:
                    return False, "Invalid"

        except urllib.error.HTTPError as e:
            if e.code == 401:
                return False, "Unauthorized"
            else:
                return False, f"HTTP {e.code}"
        except Exception as e:
            return False, str(e)

    def export_usd(self, generation_id: str, format_type: str = "usda") -> Tuple[bool, Optional[str], str]:
        """Export generation as USD/USDA.

        Args:
            generation_id: ID of the generation to export
            format_type: 'usda' or 'usdz'

        Returns:
            Tuple of (success, download_url, message)
        """
        try:
            endpoint = f"usda" if format_type == "usda" else "usdz"
            req = urllib.request.Request(
                f"{self.BASE_URL}/export/{generation_id}/{endpoint}",
                method="GET",
                headers=self.headers,
            )

            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
                download_url = data.get("url")
                if download_url:
                    return True, download_url, f"Export URL retrieved"
                else:
                    return False, None, "No URL in response"

        except urllib.error.HTTPError as e:
            error_msg = e.read().decode("utf-8")
            return False, None, f"HTTP {e.code}: {error_msg}"
        except Exception as e:
            return False, None, str(e)

    def export_usdz(self, generation_id: str) -> Tuple[bool, Optional[str], str]:
        """Export generation as USDZ (Apple format).

        Args:
            generation_id: ID of the generation to export

        Returns:
            Tuple of (success, download_url, message)
        """
        return self.export_usd(generation_id, "usdz")

    def download_usd(self, url: str, save_path: str) -> Tuple[bool, str]:
        """Download USD file to local path.

        Args:
            url: Download URL
            save_path: Local file path to save to

        Returns:
            Tuple of (success, message)
        """
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=60) as response:
                with open(save_path, "wb") as f:
                    f.write(response.read())
            return True, f"USD downloaded to {save_path}"
        except Exception as e:
            return False, str(e)

    def get_scenes(self, limit: int = 20, offset: int = 0) -> Tuple[bool, Optional[list], str]:
        """List recent generations/scenes.

        Args:
            limit: Maximum number of scenes to return
            offset: Pagination offset

        Returns:
            Tuple of (success, scenes_list, message)
        """
        try:
            req = urllib.request.Request(
                f"{self.BASE_URL}/generations?limit={limit}&offset={offset}",
                method="GET",
                headers=self.headers,
            )

            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
                scenes = data.get("data", [])
                return True, scenes, f"Retrieved {len(scenes)} scenes"

        except Exception as e:
            return False, None, str(e)

    def push_scene(self, usd_path: str, name: str = None) -> Tuple[bool, Optional[str], str]:
        """Upload USD scene to Pixibox (NOT implemented on backend).

        Note: This endpoint does not exist. Use export_usd to download scenes instead.

        Args:
            usd_path: Path to local USD/USDA file
            name: Optional scene name

        Returns:
            Tuple of (success, scene_id, message)
        """
        return False, None, "push_scene endpoint not available — export USD from Pixibox instead"
