#!/usr/bin/env bash
set -euo pipefail

BASE="https://raw.githubusercontent.com/gear66me-ui/GitHub_Sandbox/main"
TARGET="${1:-NASA_SDO_2012_TRACK_EXTRACT.py}"

curl -fsSL --retry 3 --retry-delay 1 \
  "$BASE/NASA_SDO_2012_TRACK_EXTRACT_V0002_DOWNLOAD.sh" \
  | bash -s -- "$TARGET"

python - "$TARGET" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

old = '''    values = darkness[allowed_mask]
    median, sigma = robust_scale(values)
    percentile = 97.0 if predicted is None else 92.0
'''

new = '''    mask = np.asarray(allowed_mask, dtype=bool)
    if mask.shape != darkness.shape:
        raise ValueError(
            "Venus candidate mask shape does not match the darkness image."
        )
    values = np.asarray(darkness[mask], dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return []
    median, sigma = robust_scale(values)
    percentile = 97.0 if predicted is None else 92.0
'''

count = text.count(old)
if count != 1:
    raise RuntimeError(
        f"Expected one candidate_components patch location, found {count}."
    )

text = text.replace(old, new, 1)
text = text.replace("V0002", "V0003")
path.write_text(text, encoding="utf-8")
PY

python -m py_compile "$TARGET"

python - "$TARGET" <<'PY'
from pathlib import Path
import runpy
import sys
import numpy as np

path = Path(sys.argv[1])
namespace = runpy.run_path(str(path))
CircleResult = namespace["CircleResult"]
Config = namespace["Config"]
candidate_components = namespace["candidate_components"]

result = candidate_components(
    darkness=np.zeros((16, 16), dtype=np.float32),
    allowed_mask=np.zeros((16, 16), dtype=bool),
    solar=CircleResult(8.0, 8.0, 7.0, 1.0, "TEST"),
    predicted=None,
    config=Config(Path("test.mp4"), Path("test_output")),
)
if result != []:
    raise RuntimeError("Empty-mask regression test failed.")
print("Regression test: empty Venus search mask handled correctly")
PY

SHA256="$(sha256sum "$TARGET" | awk '{print $1}')"
printf 'Downloaded and verified: %s\n' "$TARGET"
printf 'Version: V0003\n'
printf 'SHA-256: %s\n' "$SHA256"
