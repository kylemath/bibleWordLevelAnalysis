"""Download Open Scriptures Hebrew Bible WLC OSIS files."""

from __future__ import annotations

import tarfile
import urllib.request
from pathlib import Path

from bibcount.books import BOOKS

OSHB_TARBALL = "https://github.com/openscriptures/morphhb/archive/refs/heads/master.tar.gz"
OSHB_MEMBER_PREFIX = "morphhb-master/wlc/"


def download_oshb(raw_dir: Path) -> Path:
    """Fetch morphhb WLC book XML into raw_dir. Skips download if all books exist."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    missing = [b.filename for b in BOOKS if not (raw_dir / b.filename).exists()]
    if not missing:
        return raw_dir

    tarball = raw_dir / "morphhb-master.tar.gz"
    print(f"Downloading Open Scriptures Hebrew Bible ({len(missing)} books missing)...")
    urllib.request.urlretrieve(OSHB_TARBALL, tarball)
    wanted = {b.filename for b in BOOKS}
    with tarfile.open(tarball, "r:gz") as tar:
        for member in tar.getmembers():
            name = member.name
            if not name.startswith(OSHB_MEMBER_PREFIX) or not name.endswith(".xml"):
                continue
            filename = name.rsplit("/", 1)[-1]
            if filename not in wanted:
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            (raw_dir / filename).write_bytes(extracted.read())
    tarball.unlink(missing_ok=True)
    still_missing = [b.filename for b in BOOKS if not (raw_dir / b.filename).exists()]
    if still_missing:
        raise FileNotFoundError(f"OSHB download incomplete: {still_missing}")
    print(f"Wrote {len(wanted)} WLC books to {raw_dir}")
    return raw_dir
