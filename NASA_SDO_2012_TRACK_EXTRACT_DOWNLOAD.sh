#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://raw.githubusercontent.com/gear66me-ui/GitHub_Sandbox/main/NASA_SDO_2012_TRACK_EXTRACT_PARTS"
OUTPUT_FILE="${1:-NASA_SDO_2012_TRACK_EXTRACT.py}"
TEMP_FILE="${OUTPUT_FILE}.tmp"
EXPECTED_SHA256="1f8546af02e34668f965bfdb17c0a442cf6c78afa0e7af031228bd1e4eb25967"

: > "${TEMP_FILE}"
for PART in 01 02 03 04 05 06 07 08 09; do
    curl -fsSL --retry 3 --retry-delay 1 \
        "${BASE_URL}/NASA_SDO_2012_TRACK_EXTRACT_PART_${PART}.pyfrag" \
        >> "${TEMP_FILE}"
done

ACTUAL_SHA256="$(sha256sum "${TEMP_FILE}" | awk '{print $1}')"
if [[ "${ACTUAL_SHA256}" != "${EXPECTED_SHA256}" ]]; then
    echo "SHA-256 verification failed." >&2
    echo "Expected: ${EXPECTED_SHA256}" >&2
    echo "Actual  : ${ACTUAL_SHA256}" >&2
    rm -f "${TEMP_FILE}"
    exit 1
fi

mv "${TEMP_FILE}" "${OUTPUT_FILE}"
python -m py_compile "${OUTPUT_FILE}"
printf 'Downloaded and verified: %s\n' "${OUTPUT_FILE}"
printf 'SHA-256: %s\n' "${ACTUAL_SHA256}"
