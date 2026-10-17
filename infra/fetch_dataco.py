"""Fetch the user-provided public Kaggle dataset; extract only its known CSV.

Raw data stays under the ignored runtime directory and is never packaged.
"""

import argparse
import shutil
import zipfile
from pathlib import Path
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=".tradeoff/datasets")
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    target = root / "DataCoSupplyChainDataset.csv"
    if target.exists():
        print("Dataset already present:", target)
        return
    archive_path = root / "dataco.zip"
    url = "https://www.kaggle.com/api/v1/datasets/download/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis"
    with urlopen(url, timeout=45) as response, archive_path.open("wb") as destination:
        size = 0
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            size += len(block)
            if size > 256 * 1024 * 1024:
                raise ValueError("Dataset download exceeds the configured bound")
            destination.write(block)
    with zipfile.ZipFile(archive_path) as archive:
        entries = [info for info in archive.infolist() if Path(info.filename).name == target.name]
        if len(entries) != 1 or entries[0].file_size > 256 * 1024 * 1024:
            raise ValueError("Expected exactly one bounded DataCo CSV")
        with archive.open(entries[0]) as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination)
    print("Downloaded DataCo CSV:", target, "bytes:", target.stat().st_size)


if __name__ == "__main__":
    main()

