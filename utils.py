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
    if html == '': return None

    soup = BeautifulSoup(html, "html.parser", from_encoding="iso-8859-1")
    html_tag = soup.find('html', {'lang': True})
    
    if html_tag:
        lang_value = html_tag['lang']
        return lang_value

    return None

def download(warc_path: str, dest_path='', errors=None):
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

