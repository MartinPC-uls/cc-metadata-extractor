import pandas as pd
import os
import argparse
import threading
from utils import *
from itertools import islice
from warcio.archiveiterator import ArchiveIterator

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
        for record in ArchiveIterator(stream):
            if i >= max_count and max_count != 0: break
            if record.rec_type == 'response':
                warc_record_id = record.rec_headers.get_header('WARC-Record-ID')
                warc_target_uri = record.rec_headers.get_header('WARC-Target-URI')
                content_language = get_header('lang', record.http_headers.headers, exact_match=False)
                
                content = record.content_stream().read()
                records.append({
                    'WARC-File': warc,
                    'WARC-Record-ID': warc_record_id,
                    'WARC-Target-URI': warc_target_uri,
                    'Domain': get_domain_from_url(warc_target_uri).split('.')[-1],
                    'Content-Language': content_language,
                    'HTML-Language': extract_lang(content),
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

def process(path, dest_path, errors, max_count):
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
    name = out[-1].removesuffix('.warc.gz')
    print(f'Downloading {out[-1]}...')
    download(path, dest_path, errors)
    print(f'Decompressing {out[-1]}...')
    new_file = decompress_gz(f'{dest_path}/{out[-1]}', extract_path=dest_path, remove=True)
    print(f'Getting metadata from {name}...')
    records = get_metadata(new_file, max_count=max_count, remove=True)
    print(f'Saving metadata from {name}...')
    save_metadata(f'{dest_path}/{name}.csv', records)
    print(f'Done writing metadata from {name}')

def run_pipeline(paths_file: str, dest_path='', errors=None, max_count=0, num_workers=1):
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
            while True:
                batch = list(islice(file, num_workers))
                if not batch: break

                workers = []
                for line in batch:
                    worker = threading.Thread(target=process, args=(line, dest_path, errors, max_count))
                    workers.append(worker)
                    worker.start()

                for work in workers: work.join()
    except Exception as e:
        print(f'[Pipeline] An error ocurred: {e}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get all metadata from WARC files from CommonCrawl.')

    parser.add_argument('warcpaths', help="'warc.paths' file.")
    parser.add_argument('dest', help='Folder path to save metadata.')
    parser.add_argument('--num_responses', help='Number of responses to save per record (default is no limit).', required=False)
    parser.add_argument('--num_workers', help='Number of workers to process the pipeline (default is 1).', required=False)
    parser.add_argument('--errors_file', help='File to save which files failed while processing.', required=False)

    args = parser.parse_args()

    warcpaths = args.warcpaths
    dest = args.dest
    num_responses = int(args.num_responses) if args.num_responses != None else 0
    num_workers = int(args.num_workers) if args.num_workers != None else 1
    errors_file = args.errors_file

    run_pipeline(warcpaths, dest_path=dest, errors=errors_file, max_count=num_responses, num_workers=num_workers)
