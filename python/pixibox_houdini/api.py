"""
REST API client for Pixibox.ai generation and model management.

This module handles all HTTP communication with the Pixibox backend,
including authentication, generation requests, and model downloads.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin
import mimetypes

try:
    import hou
except ImportError:
    # Allow module to be imported outside Houdini for testing
    hou = None  # type: ignore


class PixiboxClient:
    """
    HTTP client for Pixibox.ai REST API.

    Handles authentication, generation requests, status polling,
    and model download management.

    Args:
        endpoint (str): Base URL of Pixibox API. Defaults to https://pixibox.ai/api
        token (str, optional): Authentication token. If not provided, reads from
                              PIXIBOX_AUTH_TOKEN environment variable.
        timeout (int): Request timeout in seconds. Default: 300.

    Example:
        >>> client = PixiboxClient(token="your-api-token")
        >>> gen_id = client.generate("text-to-3d", "A ceramic vase", "nvidia-edify")
        >>> status = client.get_generation(gen_id)
        >>> print(status["status"])  # "completed", "processing", etc
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 300,
    ) -> None:
        self.endpoint = endpoint or os.getenv(
            "PIXIBOX_API_ENDPOINT",
            "https://pixibox.ai/api"
        )
        self.token = token or os.getenv("PIXIBOX_AUTH_TOKEN", "")
        self.timeout = timeout

        if not self.token:
            raise ValueError(
                "PIXIBOX_AUTH_TOKEN not set. Set via parameter or environment."
            )

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated HTTP request to API.

        Args:
            method: HTTP method (GET, POST, etc)
            endpoint: API endpoint path (e.g. "/generations")
            data: JSON body data
            files: File upload data (not yet JSON-encoded)

        Returns:
            Parsed JSON response

        Raises:
            RuntimeError: If request fails
        """
        url = urljoin(self.endpoint, endpoint)
        headers = {
            "Authorization": f"Bearer {self.token}",
        }

        try:
            if files:
                # Multipart file upload
                import io
                body, content_type = self._encode_multipart(data or {}, files)
                headers["Content-Type"] = content_type
                request = urllib.request.Request(
                    url,
                    data=body,
                    headers=headers,
                    method=method,
                )
            else:
                # JSON request
                if data:
                    headers["Content-Type"] = "application/json"
                    body = json.dumps(data).encode("utf-8")
                else:
                    body = None
                request = urllib.request.Request(
                    url,
                    data=body,
                    headers=headers,
                    method=method,
                )

            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_data = response.read()
                return json.loads(response_data)

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise RuntimeError(
                f"API request failed ({method} {url}): "
                f"{e.code} {error_body}"
            )
        except Exception as e:
            raise RuntimeError(f"API request failed: {str(e)}")

    def _encode_multipart(
        self,
        data: Dict[str, Any],
        files: Dict[str, Any],
    ) -> tuple[bytes, str]:
        """
        Encode multipart/form-data for file uploads.

        Args:
            data: Form fields
            files: File upload data {field_name: file_path}

        Returns:
            (encoded_body, content_type_header)
        """
        import uuid
        boundary = f"----Pixibox{uuid.uuid4().hex}"
        lines = []

        # Add form fields
        for key, value in data.items():
            lines.append(f"--{boundary}".encode())
            lines.append(f'Content-Disposition: form-data; name="{key}"'.encode())
            lines.append(b"")
            lines.append(str(value).encode())

        # Add files
        for field_name, file_path in files.items():
            lines.append(f"--{boundary}".encode())
            mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            lines.append(
                f'Content-Disposition: form-data; name="{field_name}"; '
                f'filename="{os.path.basename(file_path)}"'.encode()
            )
            lines.append(f"Content-Type: {mime_type}".encode())
            lines.append(b"")

            with open(file_path, "rb") as f:
                lines.append(f.read())

        lines.append(f"--{boundary}--".encode())
        lines.append(b"")

        body = b"\r\n".join(lines)
        content_type = f"multipart/form-data; boundary={boundary}"
        return body, content_type

    def generate(
        self,
        mode: str,
        prompt: Optional[str] = None,
        image_path: Optional[str] = None,
        model: str = "nvidia-edify",
        **kwargs: Any,
    ) -> str:
        """
        Create a new 3D generation.

        Args:
            mode: "text-to-3d" or "image-to-3d"
            prompt: Text description (required for text-to-3d)
            image_path: Image file path (required for image-to-3d)
            model: AI provider (e.g. "nvidia-edify", "hunyuan-3d", "fal-gltf-generator")
            **kwargs: Additional generation options

        Returns:
            Generation ID (str)

        Example:
            >>> client = PixiboxClient(token="...")
            >>> gen_id = client.generate(
            ...     "text-to-3d",
            ...     prompt="A ceramic vase",
            ...     model="nvidia-edify"
            ... )
        """
        data: Dict[str, Any] = {
            "mode": mode,
            "model": model,
        }

        files: Dict[str, str] = {}

        if mode == "text-to-3d":
            if not prompt:
                raise ValueError("prompt required for text-to-3d")
            data["prompt"] = prompt
        elif mode == "image-to-3d":
            if not image_path:
                raise ValueError("image_path required for image-to-3d")
            files["image"] = image_path
        else:
            raise ValueError(f"Invalid mode: {mode}")

        data.update(kwargs)

        if files:
            result = self._make_request("POST", "/generations", data, files)
        else:
            result = self._make_request("POST", "/generations", data)

        return result["id"]

    def get_generation(self, generation_id: str) -> Dict[str, Any]:
        """
        Get generation status and metadata.

        Returns dict with keys:
            - id: Generation ID
            - status: "pending", "processing", "completed", "failed"
            - mode: "text-to-3d" or "image-to-3d"
            - model: AI provider name
            - prompt: Original prompt (if text-to-3d)
            - result_urls: {format: url} for completed generations
            - error: Error message if failed

        Example:
            >>> gen = client.get_generation("gen-123")
            >>> if gen["status"] == "completed":
            ...     print(gen["result_urls"]["glb"])
        """
        return self._make_request("GET", f"/generations/{generation_id}")

    def list_generations(
        self,
        limit: int = 20,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List user's past generations.

        Args:
            limit: Maximum results to return
            skip: Offset for pagination

        Returns:
            List of generation objects (see get_generation for fields)
        """
        result = self._make_request(
            "GET",
            f"/generations?limit={limit}&skip={skip}"
        )
        return result.get("items", [])

    def download_model(
        self,
        generation_id: str,
        format: str = "glb",
        output_path: Optional[str] = None,
    ) -> str:
        """
        Download generated 3D model.

        Args:
            generation_id: Generation ID
            format: Output format: "glb", "gltf", "obj"
            output_path: Where to save file. If None, uses temp dir.

        Returns:
            Local file path to downloaded model

        Raises:
            RuntimeError: If generation not completed or download fails

        Example:
            >>> gen_id = client.generate("text-to-3d", "A chair")
            >>> # ... wait for completion ...
            >>> path = client.download_model(gen_id, "glb")
            >>> print(f"Downloaded to {path}")
        """
        gen = self.get_generation(generation_id)

        if gen["status"] != "completed":
            raise RuntimeError(
                f"Generation {generation_id} not completed: {gen['status']}"
            )

        if format not in gen.get("result_urls", {}):
            available = list(gen.get("result_urls", {}).keys())
            raise RuntimeError(
                f"Format {format} not available. Available: {available}"
            )

        url = gen["result_urls"][format]

        if not output_path:
            import tempfile
            suffix = ".glb" if format == "glb" else f".{format}"
            output_file = tempfile.NamedTemporaryFile(
                suffix=suffix,
                delete=False,
            )
            output_path = output_file.name
            output_file.close()

        try:
            urllib.request.urlretrieve(url, output_path)
            return output_path
        except Exception as e:
            raise RuntimeError(f"Failed to download model: {str(e)}")

    def health_check(self) -> bool:
        """
        Check if API is reachable and authenticated.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            self._make_request("GET", "/health")
            return True
        except Exception:
            return False


def generate(
    mode: str,
    prompt: Optional[str] = None,
    image_path: Optional[str] = None,
    model: str = "nvidia-edify",
    token: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Convenience function to generate 3D model.

    Uses environment variables or parameters for authentication.

    Args:
        mode: "text-to-3d" or "image-to-3d"
        prompt: Text prompt (required for text-to-3d)
        image_path: Image file path (required for image-to-3d)
        model: AI provider name
        token: Auth token (reads PIXIBOX_AUTH_TOKEN if not provided)
        **kwargs: Additional generation options

    Returns:
        Generation ID

    Example:
        >>> gen_id = generate("text-to-3d", prompt="A wooden table")
        >>> print(f"Started generation: {gen_id}")
    """
    client = PixiboxClient(token=token)
    return client.generate(
        mode=mode,
        prompt=prompt,
        image_path=image_path,
        model=model,
        **kwargs,
    )


def get_generation(generation_id: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to get generation status.

    Args:
        generation_id: Generation ID to query
        token: Auth token (reads PIXIBOX_AUTH_TOKEN if not provided)

    Returns:
        Generation metadata dictionary
    """
    client = PixiboxClient(token=token)
    return client.get_generation(generation_id)


def list_generations(
    limit: int = 20,
    skip: int = 0,
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Convenience function to list generations.

    Args:
        limit: Maximum results
        skip: Pagination offset
        token: Auth token (reads PIXIBOX_AUTH_TOKEN if not provided)

    Returns:
        List of generation objects
    """
    client = PixiboxClient(token=token)
    return client.list_generations(limit=limit, skip=skip)


def download_model(
    generation_id: str,
    format: str = "glb",
    output_path: Optional[str] = None,
    token: Optional[str] = None,
) -> str:
    """
    Convenience function to download a model.

    Args:
        generation_id: Generation ID
        format: Output format (glb, gltf, obj)
        output_path: Output file path
        token: Auth token (reads PIXIBOX_AUTH_TOKEN if not provided)

    Returns:
        Local file path to downloaded model
    """
    client = PixiboxClient(token=token)
    return client.download_model(
        generation_id=generation_id,
        format=format,
        output_path=output_path,
    )
