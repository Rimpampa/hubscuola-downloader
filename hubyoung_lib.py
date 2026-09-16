import io
import json
import shutil
import warnings
import requests
import sqlite3
import zipfile

try:
    # pypdf (maintained fork) preferred on Python 3.12+
    from pypdf import PdfReader, PdfWriter
except ImportError:
    from PyPDF2 import PdfFileReader as PdfReader
    from PyPDF2 import PdfFileWriter as PdfWriter


def merge_pdf(extracted_files, output):
    writer = PdfWriter()

    for pdf in extracted_files:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    reader = PdfReader(io.BytesIO(pdf), strict=False)
                except TypeError:
                    # pypdf PdfReader has no strict kwarg
                    reader = PdfReader(io.BytesIO(pdf))
        except Exception as e:
            print(f"  [warn] skipping unreadable PDF chunk: {e}")
            continue

        try:
            num_pages = len(reader.pages)
        except Exception:
            # PyPDF2 1.26 fallback
            num_pages = reader.getNumPages()

        for i in range(num_pages):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    try:
                        page = reader.pages[i]
                    except Exception:
                        page = reader.getPage(i)
                try:
                    writer.add_page(page)
                except Exception:
                    writer.addPage(page)
            except Exception as e:
                print(f"  [warn] skipping broken page {i}: {e}")
                continue

    with open(output, "wb") as f:
        writer.write(f)


class HubYoung:
    def __init__(self, username: str = "", password: str = "", token: str = ""):
        self.session = requests.Session()
        self.session.headers[
            "user-agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"  # Not necessary
        self.username = username
        self.password = password
        if token:
            self.token = token
            self.session.headers["token-session"] = self.token

        if username and password:
            self.login()

    def login(self):
        mondadori_login = self.session.get(
            "https://bce.mondadorieducation.it//app/mondadorieducation/login/loginJsonp",
            params={"username": self.username, "password": self.password}).json()

        login_data = {
            "username": mondadori_login["data"]["username"],
            "sessionId": mondadori_login["data"]["sessionId"],
            "jwt": mondadori_login["data"]["hubEncryptedUser"]
        }
        internal_login = self.session.post("https://ms-api.hubscuola.it/user/internalLogin", json=login_data).json()
        self.token = internal_login["tokenId"]
        self.session.headers["token-session"] = self.token

    def get_library(self):
        return self.session.get("https://ms-api.hubscuola.it/getLibrary/young").json()

    def download_book(self, book_id, output_name):
        publication = self.session.get(
            "https://ms-mms.hubscuola.it/downloadPackage/{}/publication.zip?tokenId={}".format(book_id, self.token))
        with zipfile.ZipFile(
                io.BytesIO(publication.content)) as archive:  # Sqlite cannot open db file from bytes stream
            archive.extract("publication/publication.db")
        db = sqlite3.connect("publication/publication.db")
        cursor = db.cursor()
        query = cursor.execute("SELECT offline_value FROM offline_tbl WHERE offline_path=?",
                               ("meyoung/publication/" + book_id,)).fetchone()
        
        db.close()
        
        shutil.rmtree("./publication")

        chapter_urls = []
        for chapter in json.loads(query[0])['indexContents']['chapters']:
            chapter_urls.append(
                "https://ms-mms.hubscuola.it/public/{}/{}.zip?tokenId={}&app=v2".format(book_id, chapter["chapterId"],
                                                                                        self.token))
        pages = []
        for url in chapter_urls:
            documents = self.session.get(url)
            with zipfile.ZipFile(io.BytesIO(documents.content)) as archive:
                for file in sorted(archive.namelist()):
                    if ".pdf" in file:
                        with archive.open(file) as f:
                            pages.append(f.read())
        merge_pdf(pages, output_name)
