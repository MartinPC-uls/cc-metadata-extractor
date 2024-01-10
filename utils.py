import requests
import gzip
import shutil
import os
from urllib.parse import urlparse

BASE_URL = 'https://data.commoncrawl.org/'

def get_domain_from_url(url: str):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    return domain

def extract_tags(html_xml, tags: list, charset, default_value=None) -> dict:
    """
    Extract tags from an HTML or XML bytes or string.
    Internally, it does not parse the HTML or XML, instead it follows a string search to find 
    the requested tags. Therefore, only the first match for a tag is considered.

    Parameters:
    - html_xml: HTML or XML as bytes or string.
    - tags (list): Tags to be extracted.
    - charset: Specific encoding for HTML or XML.
    - default_value: If a tag is not found, in the returned dictionary save this value in the tag key.

    Returns:
    - dict: Dictionary containing the requested tags with their corresponding values.
    """

    content = html_xml.decode(charset, errors='replace')

    result_dict = {}
    for tag in tags:
        search_string = f'{tag}="'
        index = content.find(search_string)

        if index != -1:
            buffer = ''
            end_index = index + len(search_string)
            for c in content[end_index:]:
                if c in {'"', '\r', '\n', '{', '}', '$', '<', '>', '=', '[', ']', '.', ','}: break
                buffer += c

            if buffer == 'lang': buffer = ''
            result_dict[tag] = buffer
            continue

        result_dict[tag] = default_value

    return result_dict

def get_header(name: str, http_headers, default_value=None, exact_match=True):
        """
        Returns a header value (string verification in lower mode).

        Parameters:
        - name (str): Name of the header
        - http_headers: HTTP Headers from warcio record.
        - default_value: If there is no match for a name, this value will be returned.
        - exact_match (bool): Specify if name must be an exact match

        Returns:
        str: Value of the found header.
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

def get_warc_header(name: str, warc_headers, default_value=None):
    for header, value in warc_headers:
        if name == header:
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

    if os.path.exists(f'{dest_path}/{out}'): return

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

