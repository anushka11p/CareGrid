#!/bin/zsh
# Step 4 data: stream EAGLE-I yearly files from Figshare (10.6084/m9.figshare.24237376) and keep
# only Arizona rows. About 10 GB is streamed; about 50 MB is kept. Existing years are skipped.
set -e
ROOT=${0:A:h:h:h}
OUT="$ROOT/data/raw/eaglei"
mkdir -p "$OUT"
cd "$OUT"
for f in "coverage_history.csv 42547714" "DQI.csv 42547705" "MCC.csv 42547708"; do
  set -- ${=f}
  [[ -s $1 ]] || curl -sSL --retry 3 -o "$1" "https://ndownloader.figshare.com/files/$2"
done
fetch() {
  local year=$1 id=$2
  [[ -s az_${year}.csv ]] && return 0
  curl -sSL --retry 3 "https://ndownloader.figshare.com/files/$id" \
    | awk -F, 'NR==1 || $3=="Arizona"' > "az_${year}.csv.part" && mv "az_${year}.csv.part" "az_${year}.csv"
  echo "$year: $(wc -l < az_${year}.csv) rows"
}
for pair in "2015 42547822" "2016 42547825" "2017 42547828" "2018 42547879" "2019 42547885" \
            "2020 42547894" "2021 42547891" "2022 42547897" "2023 44574907" "2024 53581661"; do
  fetch ${=pair} &
  while (( $(jobs -r | wc -l) >= 3 )); do sleep 2; done
done
wait
