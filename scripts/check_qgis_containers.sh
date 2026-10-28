#!/usr/bin/env bash
# Download runtimes first; actual package acceptance has no network or credentials.
set -euo pipefail
if [ "$#" -ne 3 ]; then
  echo "Usage: $0 katalog-qgis.zip katalog.sqlite.zip jktz-source-dir" >&2
  exit 2
fi
package="$(realpath "$1")"
sqlite_zip="$(realpath "$2")"
jktz_source="$(realpath "$3")"
verifier="$(cd "$(dirname "$0")" && pwd)/verify_qgis_package.py"
images=(
  'qgis/qgis:3.44.15-noble@sha256:907fb2cc44adc47a8eba64316c345f0675c226d11cddea47b16ef03097caea7e'
  'qgis/qgis:4.0.1-trixie@sha256:9511f25e5e639ab89f641ea48ce3634f29f1083bf0f19f3bd35c05fd2ab351c7'
)
for image in "${images[@]}"; do
  docker pull --platform linux/amd64 "$image"
  docker run --rm --platform linux/amd64 --network none \
    --env QT_QPA_PLATFORM=offscreen \
    --env PYTHONPATH=/usr/share/qgis/python \
    --mount "type=bind,src=$verifier,dst=/verify.py,readonly" \
    --mount "type=bind,src=$package,dst=/inputs/katalog-qgis.zip,readonly" \
    --mount "type=bind,src=$sqlite_zip,dst=/inputs/katalog.sqlite.zip,readonly" \
    --mount "type=bind,src=$jktz_source,dst=/inputs/jktz,readonly" \
    "$image" /usr/bin/python3 /verify.py \
    --package /inputs/katalog-qgis.zip --sqlite-zip /inputs/katalog.sqlite.zip \
    --jktz-source-dir /inputs/jktz
done
