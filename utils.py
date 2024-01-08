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
    html_tag = soup.find('html', {'lang': True})
    
    if html_tag:
        lang_value = html_tag['lang']
        return lang_value

    return None

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

