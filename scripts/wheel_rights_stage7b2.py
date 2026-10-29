"""Read only license members of trusted PyPI wheels with bounded HTTP ranges."""

import concurrent.futures
import hashlib
import io
import json
import urllib.request
import zipfile

from scripts.stage7b2_support import OUT, read, save


class RangeReader(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.size, self.position, self.downloaded = url, size, 0, 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = (
            offset if whence == 0 else (self.position if whence == 1 else self.size) + offset
        )
        return self.position

    def read(self, size=-1):
        size = self.size - self.position if size < 0 else min(size, self.size - self.position)
        if size <= 0:
            return b""
        if size > 1024 * 1024:
            raise ValueError("Refusing a large wheel read")
        request = urllib.request.Request(
            self.url, headers={"Range": f"bytes={self.position}-{self.position + size - 1}"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 206:
                raise ValueError("Server did not honor bounded range; no full download attempted")
            data = response.read(size)
        self.position += len(data)
        self.downloaded += len(data)
        if self.downloaded > 2 * 1024 * 1024:
            raise ValueError("License metadata transfer limit exceeded")
        return data


def inspect(package):
    name = package["name"]
    try:
        with urllib.request.urlopen(package["source"], timeout=30) as response:
            metadata = json.load(response)
        wheels = [x for x in metadata["urls"] if x["packagetype"] == "bdist_wheel"]
        wheel = next(
            (x for x in wheels if "x86_64" in x["filename"]), min(wheels, key=lambda x: x["size"])
        )
        stream = RangeReader(wheel["url"], wheel["size"])
        notices = []
        with zipfile.ZipFile(stream) as archive:
            for entry in archive.infolist():
                base = entry.filename.rsplit("/", 1)[-1].lower()
                if not base.startswith(("license", "licence", "copying", "notice")):
                    continue
                if entry.file_size > 1024 * 1024:
                    raise ValueError("License file is unexpectedly large")
                data = archive.read(entry)
                target = OUT / "wheel-rights-sources" / name / base
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                notices.append(
                    {
                        "member": entry.filename,
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "bytes": len(data),
                        "crc_verified_by_zipfile": True,
                        "opening": data.decode("utf-8", errors="replace")[:600],
                    }
                )
        return {
            "name": name,
            "version": package["version"],
            "source": wheel["url"],
            "published_wheel_sha256": wheel["digests"]["sha256"],
            "wheel_size": wheel["size"],
            "license_only_bytes_transferred": stream.downloaded,
            "full_wheel_downloaded_or_executed": False,
            "notices": notices,
        }
    except Exception as exc:
        return {"name": name, "error": str(exc)}


def main():
    wanted = {
        "cuda-toolkit",
        "nvidia-cuda-runtime",
        "nvidia-cudnn-cu13",
        "nvidia-nccl-cu13",
        "nvidia-nvshmem-cu13",
        "nvidia-nvtx",
    }
    packages = [p for p in read("package-rights-evidence.json") if p["name"] in wanted]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        rows = list(executor.map(inspect, packages))
    save("wheel-rights-review.json", rows)
    for row in rows:
        print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
