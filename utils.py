import requests
import gzip
import shutil
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse

BASE_URL = 'https://data.commoncrawl.org/'

def get_domain_from_url(url: str):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    return domain

def extract_lang(html: str):
    """
    Extracts the HTML Lang Tag if found. Otherwise it returns None.

    Parameters:
    - html (str): HTML code as string.

    Returns:
    str: HTML Language.
    """
    if html == '': return None

    soup = BeautifulSoup(html, "html.parser", from_encoding="iso-8859-1")

    lang_tag = soup.find('html', {'lang': True}) or soup.find('html', {'xml:lang': True})
    return lang_tag.get('lang') or lang_tag.get('xml:lang') if lang_tag else None

def extract_dir(html: str):
    """
    Extracts the HTML Dir Tag if found. Otherwise it returns None.

    Parameters:
    - html (str): HTML code as string.

    Returns:
    str: HTML Dir.
    """
    if html == '': return None

    soup = BeautifulSoup(html, "html.parser", from_encoding="iso-8859-1")

    dir_tag = soup.find('html', {'dir': True})
    return dir_tag.get('dir') if dir_tag else None

def get_header(name: str, http_headers, default_value=None, exact_match=True):
        """
        Returns a header value (string verification in lower mode).

        Parameters:
        - name (str): Name of the header
        - http_headers: HTTP Headers from warcio record.
        - default_value: If there is no match for a name, this value will be returned.
        - exact_match (bool): Specify if name must be an exact match
        """

        # The approach is quite similar to warcio package, although we check either for an
        # exact match or if name is contained.

        name_lower = name.lower()

        if exact_match:
            for header, value in http_headers:
                if name_lower == header.lower():
                    return value
        else:
            for header, value in http_headers:
                if name_lower in header.lower():
                    return value

        return default_value

def download(warc_path: str, dest_path='', errors=None):
    """
    Downloads a single WARC path and saves it into a destionation folder.

    Parameters:
    - warc_path (str): WARC path to be downloaded (without base URL).
    - dest_path (str): Destionation folder to save the WARC record (default is the current directory).
    - errors (str): File to save the corresponding WARC path if the download failed (default is None, that means no errors file).
    """
    url = BASE_URL + warc_path
    out = warc_path.split('/')[-1]
    if dest_path != '' and (dest_path[-1] != '/' or dest_path[-1] != '\\'):
        dest_path = f'{dest_path}/{out}'
    else:
        dest_path = out

    response = requests.get(url)

    if response.status_code == 200:
        with open(dest_path, 'wb') as file:
            file.write(response.content)
        file.close()
        print(f'File downloaded successfully to {dest_path}')
    else:
        if errors != None:
            with open(errors, 'a') as file:
                file.write(f'{warc_path}\n')
        
        print(f'Failed to download file. Status code: {response.status_code}')

def decompress_gz(file_path: str, extract_path: str, remove=False):
    """
    Decompress a GZip file.

    Parameters:
    - file_path (str): File path to extract.
    - extract_path (str): Path to save the extracted file.
    - remove (bool): Wether you want to remove the compressed file after decompressing or not (default is False).

    Returns:
    str: Path to the extracted file.
    """
    name = file_path.split('/')[-1].removesuffix('.gz')
    output = f'{extract_path}/{name}'

    try:
        with gzip.open(file_path, 'rb') as gz_file, open(output, 'wb') as out_file:
            shutil.copyfileobj(gz_file, out_file)

        if remove:
            os.remove(file_path)

        return output
    except Exception as e:
        print(f'[Decompression] An error ocurred: {e}')

