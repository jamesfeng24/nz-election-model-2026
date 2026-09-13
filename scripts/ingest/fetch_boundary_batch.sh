#!/bin/sh
# Fetch only explicitly reviewed URL/path pairs. Existing raw files are never replaced.
set -eu
while IFS="$(printf '\t')" read -r url destination; do
  case "$destination" in data/raw/boundaries/*) ;; *) echo 'Invalid boundary destination' >&2; exit 1;; esac
  if [ -e "$destination" ]; then continue; fi
  mkdir -p "$(dirname "$destination")"
  curl --fail --location --retry 2 --connect-timeout 20 --max-time 180 "$url" --output "$destination.part"
  mv "$destination.part" "$destination"
done < "$1"
