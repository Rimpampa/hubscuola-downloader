import argparse
import getpass
import os
import sys
import unicodedata

from hubyoung_lib import HubYoung


def safe_filename(title: str) -> str:
    slug = unicodedata.normalize(
        "NFD", title.lower().replace(" ", "_")
    ).encode("ascii", "ignore").decode("ascii")
    return slug


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Download books from HUBScuola (Mondadori) and save them as PDFs."
    )
    parser.add_argument(
        "username",
        nargs="?",
        default=os.environ.get("HUB_USER", ""),
        help="HUBScuola email (or set HUB_USER env var)",
    )
    parser.add_argument(
        "password",
        nargs="?",
        default=os.environ.get("HUB_PASS", ""),
        help="HUBScuola password (or set HUB_PASS env var)",
    )
    parser.add_argument(
        "--all",
        dest="download_all",
        action="store_true",
        help="download all books without prompting",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    print("*" * 10, "HubYoung downloader by @vvettoretti", "*" * 10)
    args = parse_args(argv)

    username = args.username or input("Enter email\n")
    password = args.password or getpass.getpass("Enter password\n")

    h = HubYoung(username, password)

    print("Logged in successfully")

    library = h.get_library()
    if not library:
        print("No books found in your library.")
        return 0

    books_to_download = []
    if args.download_all:
        books_to_download = list(library)
        print(f"Downloading all {len(books_to_download)} book(s) (--all given)")
    else:
        for book in library:
            print(book["title"])
            print("ID -", book["id"])
            if input("Download? (y/n)\n").lower() == "y":
                books_to_download.append(book)

    for book in books_to_download:
        output_name = f"{book['id']}_{safe_filename(book['title'])}.pdf"
        print(f"Downloading {book['title']}... (this may take a while)")
        h.download_book(str(book["id"]), output_name)
        print(f"Saved {output_name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
