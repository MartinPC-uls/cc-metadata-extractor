import pandas as pd
import os
import argparse
from utils import *
from itertools import islice
from fastwarc.warc import ArchiveIterator, WarcRecordType
from concurrent.futures import ThreadPoolExecutor

VERBOSE = False

def get_metadata(warc_path, max_count=0, remove=False):
    """
    Get metadata from a WARC file path.

    Parameters:
    - warc_path (str): WARC file path to extract the metadata.
    - max_count (int): Max number of responses to get from a WARC path (default is 0).
    - remove (bool): Wether you want to remove the .warc file or not.

    Returns:
    list: The list of records found.
    """
    warc = warc_path.split('.')[0].split('/')[-1] # second split in case that it's a folder path

    i = 0
    records = []
    with open(warc_path, 'rb') as stream:
        for record in ArchiveIterator(stream, record_types=WarcRecordType.response):
            if i >= max_count and max_count != 0: break
            content_type = record.http_content_type
            if not content_type: continue

            content_type = content_type.replace(';', ' ').split()[0]
            if not content_type or content_type not in {'text/html', 'application/xhtml+xml'}: continue

            warc_record_id = record.record_id
            warc_target_uri = get_warc_header('WARC-Target-URI', record.headers)
            content_language = get_header('Content-Language', record.http_headers, exact_match=True)

            content = record.reader.read(200)

            extracted_tags = extract_tags(content, ['lang', 'dir'], record.http_charset or 'utf-8')

            records.append({
                'WARC_File': warc,
                'WARC_Record_ID': warc_record_id,
                'WARC_Target_URI': warc_target_uri,
                'Domain': get_domain_from_url(warc_target_uri).split('.')[-1],
                'Content_Language': content_language,
                'HTML_Language': extracted_tags['lang'],
                'HTML_Dir': extracted_tags['dir']
            })

            i += 1

    if remove:
        os.remove(warc_path)

    return records

def save_metadata(dest: str, records: list):
    """
    Saves the metadata to a CSV file.

    Parameters:
    - dest (str): Path to save the CSV file.
    - records (list): List of records found in a WARC path.
    """
    df = pd.DataFrame(records)

    df.to_csv(dest, index=False)

def process(path, dest_path, errors, max_count, decompression=True):
    """
    Runs a single pipeline process.

    Parameters:
    - path (str): Path to the .warc.gz file that contains WARC paths (contained in warc.paths).
    - dest_path (str): Path to the destionation where you want to save all the process.
    - errors (str): Path to the errors file.
    - max_count (int): Max number of responses to get from a WARC path.
    """
    path = path.strip()
    out = path.split('/')
    file = out[-1]
    name = file.removesuffix('.warc.gz')

    if os.path.exists(f'{dest_path}/{name}.csv'):
        #print(f'Skipping process for {name} since it already exists.')
        return

    if VERBOSE: print(f'Downloading {file}...')
    download(path, dest_path, errors, verbose=VERBOSE)

    new_file = None
    if decompression:
        if VERBOSE: print(f'Decompressing {file}...')
        new_file = decompress_gz(f'{dest_path}/{file}', extract_path=dest_path, remove=True)
    
    if VERBOSE: print(f'Getting metadata from {name}...')
    records = get_metadata(new_file or f'{dest_path}/{file}', max_count=max_count, remove=True)

    if VERBOSE: print(f'Saving metadata from {name}...')
    save_metadata(f'{dest_path}/{name}.csv', records)

    if VERBOSE: print(f'Done writing metadata from {name}')

def run_pipeline(paths_file: str, dest_path='', errors=None, max_count=0, num_workers=1, decompression=True):
    """
    Runs the whole extraction pipeline.

    Parameters:
    - paths_file (str): warc.paths file path.
    - dest_path (str): Destination path to save all the process (defaults to the current directory).
    - errors (str): Path to the errors file (defaults to None, that means no errors file)
    - max_count (int): Max number of responses to get from a WARC path (default is 0).
    - num_workers (int): Number of workers to run the pipeline (default is 1).
    """
    try:
        with open(paths_file, 'r') as file:
            completed = 0
            while True:
                batch = list(islice(file, num_workers))
                if not batch: break

                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    features = {executor.submit(process, line, dest_path, errors, max_count, decompression) for line in batch}

                    for future in features:
                        try:
                            future.result()
                            completed += 1
                            print(f'Progress: {completed}/90000')
                        except Exception as e:
                            print(f"Error: {e}")
    except Exception as e:
        print(f'[Pipeline] An error ocurred: {e}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get all metadata from WARC files from CommonCrawl.')

    parser.add_argument('warcpaths', help="'warc.paths' file.")
    parser.add_argument('dest', help='Folder path to save metadata.')
    parser.add_argument('--num_responses', help='Number of responses to save per record (default is no limit).', required=False)
    parser.add_argument('--num_workers', help='Number of workers to process the pipeline (default is 1).', required=False)
    parser.add_argument('--errors_file', help='File to save which files failed while processing.', required=False)
    parser.add_argument('--without_decompression', help='Removes decompression from pipeline.', action='store_true')
    parser.add_argument('--verbose', help='Activates verbose mode.', action='store_true')

    args = parser.parse_args()

    warcpaths = args.warcpaths
    dest = args.dest
    num_responses = int(args.num_responses) if args.num_responses != None else 0
    num_workers = int(args.num_workers) if args.num_workers != None else 1
    errors_file = args.errors_file
    without_decompression = args.without_decompression
    VERBOSE = args.verbose

    run_pipeline(warcpaths, dest_path=dest, errors=errors_file, max_count=num_responses,
                 num_workers=num_workers, decompression=not without_decompression)
