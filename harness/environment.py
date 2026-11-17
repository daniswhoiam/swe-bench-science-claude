"""The benchmark's offline Docker environment, with a configurable Ubuntu mirror for
the egress-proxy image build.

Pier builds its squid proxy image from ubuntu:24.04 with an apt-get against
archive.ubuntu.com, which hangs over HTTP from this network. Only that proxy build is
changed; task images and the benchmark's network policy checks are inherited as-is.

Select it with:
    --environment-import-path harness.environment:MirroredScienceBenchDocker
    --environment-kwarg ubuntu_mirror=http://de.archive.ubuntu.com/ubuntu
"""
from __future__ import annotations

from scripts.pier_network import ScienceBenchDocker

DEFAULT_MIRROR = "http://ftp.fau.de/ubuntu"


class MirroredScienceBenchDocker(ScienceBenchDocker):
    def __init__(self, *args, ubuntu_mirror: str = DEFAULT_MIRROR, **kwargs):
        self._ubuntu_mirror = ubuntu_mirror.rstrip("/")
        super().__init__(*args, **kwargs)

    def _prepare_egress_proxy_compose(self) -> None:
        super()._prepare_egress_proxy_compose()
        if not self._egress_proxy_compose_path:
            return
        dockerfile = self._egress_proxy_compose_path.parent / "egress-proxy" / "Dockerfile"
        base = "FROM ubuntu:24.04\n"
        text = dockerfile.read_text()
        if not text.startswith(base):
            raise RuntimeError("Unsupported Pier proxy Dockerfile; expected datacurve-pier 0.3.0")
        switch = (
            "RUN sed -i -E "
            f"'s#http://(archive|security)\\.ubuntu\\.com/ubuntu/?#{self._ubuntu_mirror}/#g' "
            "/etc/apt/sources.list.d/ubuntu.sources\n"
        )
        dockerfile.write_text(base + switch + text[len(base):])
