#!/usr/bin/env bash
# Run from repository root. Public GUGiK snapshots are kept verbatim.
# The 2025 pilot's workflow is reused, but 2025 has no indexed coverage here.
set -euo pipefail
lidar_dir=build/research/mylna-2026-10-24
mkdir -p "$lidar_dir"
query_index() {
  curl -fLsS --get "https://mapy.geoportal.gov.pl/wss/service/PZGIK/$1/WFS/Skorowidze" \
    --data-urlencode service=WFS --data-urlencode version=2.0.0 \
    --data-urlencode request=GetFeature --data-urlencode "typenames=$2" \
    --data-urlencode srsname=EPSG:4326 --data-urlencode "bbox=$3,urn:ogc:def:crs:EPSG::4326" \
    -o "$lidar_dir/$4"
}
query_index DanePomiaroweLidarEVRF2007 gugik:SkorowidzDanychPomiarowychLIDAR2025 49.2387,19.8605,49.2412,19.8640 lidar-2025-index.xml
query_index DanePomiaroweLidarEVRF2007 gugik:SkorowidzDanychPomiarowychLIDAR2018,gugik:SkorowidzDanychPomiarowychLIDAR2019,gugik:SkorowidzDanychPomiarowychLIDAR2020,gugik:SkorowidzDanychPomiarowychLIDAR2021,gugik:SkorowidzDanychPomiarowychLIDAR2022,gugik:SkorowidzDanychPomiarowychLIDAR2023,gugik:SkorowidzDanychPomiarowychLIDAR2024,gugik:SkorowidzDanychPomiarowychLIDAR2025,gugik:SkorowidzDanychPomiarowychLIDAR2026 49.2387,19.8605,49.2412,19.8640 lidar-all-years-index.xml
query_index DanePomiaroweLidarEVRF2007 gugik:SkorowidzDanychPomiarowychLIDAR2023,gugik:SkorowidzDanychPomiarowychLIDAR2025 49.230,19.850,49.250,19.930 lidar-broad-index.xml
query_index DanePomiaroweLidarKRON86 gugik:SkorowidzDanychPomiarowychLIDAR2010,gugik:SkorowidzDanychPomiarowychLIDAR2011,gugik:SkorowidzDanychPomiarowychLIDAR2012,gugik:SkorowidzDanychPomiarowychLIDAR2013,gugik:SkorowidzDanychPomiarowychLIDAR2014,gugik:SkorowidzDanychPomiarowychLIDAR2015,gugik:SkorowidzDanychPomiarowychLIDAR2016,gugik:SkorowidzDanychPomiarowychLIDAR2017,gugik:SkorowidzDanychPomiarowychLIDAR2018,gugik:SkorowidzDanychPomiarowychLIDAR2019 49.2387,19.8605,49.2412,19.8640 lidar-kron-index.xml
curl -fLsS --retry 2 'https://opendata.geoportal.gov.pl/NumDaneWys/DanePomiaroweLAZ/4979/4979_281506_M-34-100-B-c-2-2-2.laz' -o "$lidar_dir/mylna-2012-north-source.laz"
curl -fLsS --retry 2 'https://opendata.geoportal.gov.pl/NumDaneWys/DanePomiaroweLAZ/4979/4979_281508_M-34-100-B-c-2-2-4.laz' -o "$lidar_dir/mylna-2012-south-source.laz"
# Reproduction Python dependency versions are recorded in acquisition.json.
# Invoke the accompanying crop.py with laspy, lazrs, numpy and pyproj installed.
