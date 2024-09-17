#!.\venv\Scripts\python.exe
# template courtesy of https://adamj.eu/tech/2021/10/09/a-python-script-template-with-and-without-type-hints-and-async/

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import glob

import requests
from colorama import Fore, Style


def get_asset_ids(page: int):
    assets = {}
    try:
        response = json.loads(
            (
                requests.get(url=f"https://quixel.com/v1/assets?limit=200&page={page}")
            ).text
        )
        for asset in response["assets"]:
            assets.update(
                {
                    asset["_id"]: {
                        "name": asset["name"],
                        "categories": asset["categories"],
                    }
                }
            )
        # print(Fore.GREEN, f"Checking page {page} succeeded!")
    except:
        return 0
        # print(Fore.RED, f"Checking page {page} failed!")

    return assets


def acquire_asset(id):
    try:
        print(Fore.YELLOW + f"Acquiring asset with ID {id}")
        response = requests.post(
            "https://quixel.com/v1/acl",
            data={"assetID": id},
            headers={"Authorization": bearer},
        )
        print(Fore.GREEN + f"Acquired asset {id}!")
    except:
        print(Fore.RED + f"Failed to acquire asset {id}!")


def download_asset(id: str):
        if id in downloaded:
            print(Fore.GREEN+f"{id} already downloaded!")
        else:
                    payload = {
            "asset": id,
            "config": {
                "highpoly": False,
                "albedo_lods": False,
                "lowerlod_normals": False,
                "ztool": False,
                "brushes": False,
                "meshMimeType": "application/x-fbx",
            },
        }

        # print(payload)
        response = json.loads(
            (
                requests.post(
                    "https://quixel.com/v1/downloads",
                    json=payload,
                    headers={"Authorization": bearer},
                )
            ).text
        )
        url = f'https://assetdownloads.quixel.com/download/{response['id']}?preserveStructure=true&url=https%3A%2F%2Fquixel.com%2Fv1%2Fdownloads'
        print(Fore.YELLOW, f"Downloading {url}...")
        download = requests.get(url)
        filename = (download.headers["Content-Disposition"]).split("filename=")[-1]
        foldername = "uncategorized"
        if (filename.split("_")[-2]) in ["3d","3dplant","atlas","brush","surface"]:
            foldername = (filename.split("_")[-2])
        filename = os.path.join(f"{downloadPath}", foldername, filename)

        with open(filename, "wb") as f:
            f.write(download.content)

            if os.path.exists(filename):
                downloaded.append(filename.split("_2K")[0].split("_4K")[0].split("_8K")[0].split("_")[-1])
                print(Fore.GREEN, f"{filename} successfully downloaded! ({len(downloaded)}/{total})")
            else:
                print(Fore.RED, f"{filename} download unsuccessful!")
        


def main(argv: Sequence[str] | None = None) -> int:
    start = datetime.now()

    parser = argparse.ArgumentParser()
    # Add arguments here (https://docs.python.org/3/library/argparse.html)
    parser.add_argument("--token", type=str, required=True)
    parser.add_argument("--downloadPath", type=str, required=True)
    parser.add_argument("--refreshToken", type=str, required=False)
    args = parser.parse_args(argv)

    # Start writing code here
    print(
        Fore.BLUE
        + Style.BRIGHT
        + "Running python-quixel-downloader from: "
        + Style.DIM
        + os.getcwd()
        + Style.RESET_ALL
    )

    global bearer
    bearer = f"Bearer {args.token}"

    global downloadPath
    downloadPath = os.path.abspath(args.downloadPath)

    # get some initial data
    api_categorytree = json.loads(
        (requests.get(url="https://quixel.com/v1/assets/categorytree/v3")).text
    )
    api_assets = json.loads(
        (requests.get(url=f"https://quixel.com/v1/assets?limit=200&page=1")).text
    )
    print(Fore.YELLOW + f"Total quixel assets: {api_assets['total']}")

    # Request list of asset IDs and info
    pages = range(1, int(api_assets["pages"] + 1))
    assets = {}
    with ThreadPoolExecutor(max_workers=32) as executor:
        print(Fore.YELLOW + f"Checking {api_assets['pages']} pages...")
        responses = list(executor.map(get_asset_ids, pages))
    for response in responses:
        assets.update(response)
    print(f"Found {len(assets)} assets!")

    global total
    global new_assets
    total = len(assets)

    # Load asset dictionary
    if not os.path.exists(".\\megascans.json"):
        with open(".\\megascans.json", "w") as f:
            f.write(json.dumps(dict(), indent=4, sort_keys=True))
            print("created megascans.json")

    with open(".\\megascans.json", "r") as f:
        f_assets = json.loads(f.read())
        print(f"Loaded {len(f_assets)} assets!")

        print(f"Found {len(assets) - len(f_assets)} new assets")
        new_assets = set(assets) - set(f_assets)
        assets = assets | f_assets

    print(f"Found {len(new_assets)} unacquired assets!")
    
    # Save asset dictionary
    with open(".\\megascans.json", "w") as f:
        f.write(json.dumps(assets, indent=4, sort_keys=True))
        print(f"Recorded {len(assets)} assets!")

    # acquire all assets
    with ThreadPoolExecutor(max_workers=32) as executor:
        executor.map(acquire_asset, new_assets)

    # Create list of downloaded assets
    global downloaded
    downloaded = []
    for file in glob.glob(f"{downloadPath}\\*\\*.zip"):
        downloaded.append(file.split("_2K")[0].split("_4K")[0].split("_8K")[0].split("_")[-1])

    print(Fore.RED+f"Found {len(downloaded)} assets already downloaded!")

    # Download assets
    with ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(download_asset, assets)

    # reset terminal colors
    print(Style.RESET_ALL)
    print(datetime.now() - start)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
