"""Memory-efficient Hebrew Bible word index."""

from bibcount.query import TanakhIndex, WordHit
from bibcount.paths import parsed_dir, raw_dir

__all__ = ["TanakhIndex", "WordHit", "parsed_dir", "raw_dir"]
