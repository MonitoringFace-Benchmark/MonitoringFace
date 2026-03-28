import os
import io
import shutil
import tarfile
import docker
from docker.errors import APIError

from Infrastructure.Builders.BuilderUtilities import image_building, ImageBuildException, image_exists


def build_pipeline(path_to_dockerfile: str, image_name: str, tmp_binary_location: str) -> tuple[str, str]:
    """
    Build a Docker image and extract its binary to a temporary location.

    Args:
        path_to_dockerfile: Path to the directory containing the Dockerfile
        image_name: Name to tag the built Docker image with
        tmp_binary_location: Path where the extracted binary should be stored

    Returns:
        Tuple of (extracted_binary_path, binary_name) where:
        - extracted_binary_path: Full path to the extracted binary
        - binary_name: Name of the binary (filename only)

    Raises:
        ImageBuildException: If the Docker image build fails
        APIError: If Docker API operations fail
        Exception: If binary extraction fails
    """
    # todo exists and version verification
    # should be done by the ToolImageManager
    if not image_exists(image_name):
        if not image_building(image_name, path_to_dockerfile):
            raise ImageBuildException(f"Failed to build image: {image_name}")
    else:
        print(f"Image {image_name} already exists. Skipping build.")

    client = docker.from_env()
    extracted_binary_path = None
    binary_name = None
    try:
        container = client.containers.create(image_name, detach=True)
        try:
            os.makedirs(tmp_binary_location, exist_ok=True)
            if not os.access(tmp_binary_location, os.W_OK):
                raise PermissionError(f"Destination directory {tmp_binary_location} is not writable")

            try:
                archive_bytes, _ = container.get_archive("/usr/local/bin")
                tar_stream = io.BytesIO(b"".join(archive_bytes))
                with tarfile.open(fileobj=tar_stream, mode='r:*') as tar:
                    tar.extractall(path=tmp_binary_location)
                print(f"Binary extracted successfully from /usr/local/bin to {tmp_binary_location}")
                extracted_binary_path = tmp_binary_location
                # For multi-stage builds, return the directory as the binary location
                binary_name = "bin"
            except APIError:
                archive_bytes, _ = container.get_archive("/")
                tar_stream = io.BytesIO(b"".join(archive_bytes))
                with tarfile.open(fileobj=tar_stream, mode='r:*') as tar:
                    for member in tar.getmembers():
                        if member.name == '/' or member.name.startswith('/.') or '/' in member.name.lstrip('/'):
                            continue
                        if member.isfile():
                            try:
                                tar_obj = tar.extractfile(member)
                                dst_path = os.path.join(tmp_binary_location, member.name.lstrip('/'))
                                dst_dir = os.path.dirname(dst_path)
                                os.makedirs(dst_dir, exist_ok=True)
                                if os.path.exists(dst_path):
                                    os.remove(dst_path)
                                with open(dst_path, 'wb') as dst_file:
                                    shutil.copyfileobj(tar_obj, dst_file)
                                os.chmod(dst_path, 0o755)
                                if extracted_binary_path is None:
                                    extracted_binary_path = dst_path
                                    binary_name = os.path.basename(dst_path)
                            except OSError as e:
                                print(f"Warning: Failed to extract {member.name}: {e}")
                                continue
                print(f"Binary extracted successfully from root to {tmp_binary_location}")
        finally:
            container.remove(force=True)
    except APIError as e:
        raise APIError(f"Docker API error during binary extraction: {e}")
    except Exception as e:
        raise Exception(f"Error extracting binary from image {image_name}: {e}")

    if extracted_binary_path is None or binary_name is None:
        raise Exception(f"Failed to extract binary from image {image_name}")

    return extracted_binary_path, binary_name


def build_with_extracted_binary(
        path_to_secondary_dockerfile: str, secondary_image_name: str,
        extracted_binary_path: str, binary_name: str,
        binary_destination: str = "/tool"
) -> bool:
    """
    Build a secondary Docker image that includes an extracted binary from a previous build.

    This function copies the extracted binary into the Docker build context and builds a new image.
    The secondary Dockerfile should include a COPY instruction to add the binary.

    Args:
        path_to_secondary_dockerfile: Path to the directory containing the secondary Dockerfile
        secondary_image_name: Name to tag the secondary Docker image with
        extracted_binary_path: Path to the extracted binary from build_pipeline()
        binary_name: Name of the binary (filename) returned by build_pipeline()
        binary_destination: Destination path in the Docker image (default: "/tool")

    Returns:
        True if build succeeded, False otherwise

    Raises:
        FileNotFoundError: If extracted binary doesn't exist

    Example:
        # Dockerfile example:
        # FROM scratch
        # COPY tool /tool
        # ENTRYPOINT ["/tool"]

        # Python usage:
        # 1. Build and extract binary from first image
        binary_path, binary_name = build_pipeline(
            "/path/to/first/dockerfile",
            "image-one",
            "/tmp/extracted"
        )

        # 2. Build second image using the extracted binary
        success = build_with_extracted_binary(
            "/path/to/second/dockerfile",
            "image-two",
            binary_path,
            binary_name,
            "/tool"
        )
    """
    if not os.path.exists(extracted_binary_path):
        raise FileNotFoundError(f"Extracted binary not found at {extracted_binary_path}")

    build_context_dir = path_to_secondary_dockerfile
    binary_in_context = os.path.join(build_context_dir, binary_name)

    try:
        # Copy binary to build context
        if extracted_binary_path != binary_in_context:
            shutil.copy2(extracted_binary_path, binary_in_context)
            print(f"Copied binary '{binary_name}' to build context: {binary_in_context}")

        # Build the secondary image
        success = image_building(secondary_image_name, build_context_dir)
        if success:
            print(f"Secondary image '{secondary_image_name}' built successfully with binary at {binary_destination}")
        return success
    finally:
        if extracted_binary_path != binary_in_context and os.path.exists(binary_in_context):
            os.remove(binary_in_context)
            print(f"Cleaned up temporary binary from build context")

if __name__ == "__main__":
    # Example usage: Two-stage build process
    try:
        # Stage 1: Build first image and extract binary
        print("=== Stage 1: Building first image and extracting binary ===")
        binary_path, binary_name = build_pipeline(
            "/Users/krq770/PycharmProjects/MonitoringFace_curr/Archive/Tools/TimelyMon/online",
            "timely-standalone",
            "/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure/build/Monitor/Test"
        )
        print(f"Extracted binary: {binary_path} (name: {binary_name})")

        # Stage 2: Build second image using the extracted binary
        print("\n=== Stage 2: Building second image with extracted binary ===")
        success = build_with_extracted_binary(
            "/Users/krq770/PycharmProjects/MonitoringFace_curr/Archive/Tools/TestMinimal",
            "timely-runner",
            binary_path,
            binary_name,
            "/usr/local/bin/timelymon"
        )

        if success:
            print("Successfully built secondary image with extracted binary!")
        else:
            print("Failed to build secondary image")

    except ImageBuildException as e:
        print(f"Image build failed: {e}")
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except Exception as e:
        print(f"Error: {e}")
