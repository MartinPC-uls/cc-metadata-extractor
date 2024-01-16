import pandas as pd
import os
import argparse
import threading
from utils import *
from itertools import islice
from fastwarc.warc import ArchiveIterator, WarcRecordType

## Defaults ##
TEST_PATH = None
## Defaults ##

def get_text(wet_path, max_count=0, remove=False):
    """
    Get content from a WET file path.

    Parameters:
    - wet_path (str): WET file path to extract the content.
    - max_count (int): Max number of responses to get from a WET path (default is 0).
    - remove (bool): Wether you want to remove the .warc.wet file or not.

    Returns:
    list: The list of records found.
    """
    wet = wet_path.split('.')[0].split('/')[-1] # second split in case that it's a folder path

    if TEST_PATH:
        path = f'{TEST_PATH}/{wet}.csv'
        if not os.path.exists(path):
            print(f'"{path}" was not found. Finishing process...')
            exit()
        
        _records = pd.read_csv(path, index_col='WARC-Record-ID')

    i = 0
    records = []
    with open(wet_path, 'rb') as stream:
        for record in ArchiveIterator(stream):
            if i >= max_count and max_count != 0: break
            content_type = get_warc_header('Content-Type', record.headers)
            if not content_type: continue
            if content_type != 'text/plain': continue

            warc_refers_to = get_warc_header('WARC-Refers-To', record.headers)
            content = record.reader.read().decode('utf-8', errors='replace')

            if not TEST_PATH:
                warc_record_id = record.record_id
                content_language = get_warc_header('WARC-Identified-Content-Language', record.headers)

                records.append({
                    'WARC-File': wet,
                    'WARC-Record-ID': warc_record_id,
                    'WARC-Refers-To': warc_refers_to,
                    'WARC-Identified-Content-Language': content_language,
                    'Content': content
                })
            else:
                try:
                    lang = _records.at[warc_refers_to, 'HTML-Language']
                    print(f'"{content[:20]}" --> {lang}')
                except KeyError:
                    print('Key error')
                    pass

            i += 1

    if remove:
        os.remove(wet_path)

    return records

def save_content(dest: str, records: list):
    """
    Saves the content to a CSV file.

    Parameters:
    - dest (str): Path to save the CSV file.
    - records (list): List of records found in a WET path.
    """
    df = pd.DataFrame(records)

    df.to_csv(dest, index=False)

def process(path, dest_path, errors, max_count, decompression=True):
    """
    Runs a single pipeline process.

    Parameters:
    - path (str): Path to the .warc.wet.gz file that contains WET paths (contained in warc.paths).
    - dest_path (str): Path to the destionation where you want to save all the process.
    - errors (str): Path to the errors file.
    - max_count (int): Max number of responses to get from a WET path.
    """
    path = path.strip()
    out = path.split('/')
    file = out[-1]
    name = file.removesuffix('.warc.wet.gz')

    if os.path.exists(f'{dest_path}/{name}.wet.csv'):
        print(f'Skipping process for {name} since it already exists.')
        return

    print(f'Downloading {file}...')
    download(path, dest_path, errors)

    new_file = None
    if decompression:
        print(f'Decompressing {file}...')
        new_file = decompress_gz(f'{dest_path}/{file}', extract_path=dest_path, remove=True)
    
    print(f'Getting content from {name}...')
    records = get_text(new_file or f'{dest_path}/{file}', max_count=max_count, remove=True)

    if not TEST_PATH:
        print(f'Saving content from {name}...')
        save_content(f'{dest_path}/{name}.wet.csv', records)
        print(f'Done writing content from {name}')
    else:
        print(f'Done testing for {name}')

def run_pipeline(paths_file: str, dest_path='', errors=None, max_count=0, num_workers=1, decompression=True):
    """
    Runs the whole extraction pipeline.

    Parameters:
    - paths_file (str): warc.paths file path.
    - dest_path (str): Destination path to save all the process (defaults to the current directory).
    - errors (str): Path to the errors file (defaults to None, that means no errors file)
    - max_count (int): Max number of responses to get from a WET path (default is 0).
    - num_workers (int): Number of workers to run the pipeline (default is 1).
    """
    try:
        with open(paths_file, 'r') as file:
            while True:
                batch = list(islice(file, num_workers))
                if not batch: break

                workers = []
                for line in batch:
                    worker = threading.Thread(target=process, args=(line, dest_path, errors, max_count, decompression))
                    workers.append(worker)
                    worker.start()

                for work in workers: work.join()
    except Exception as e:
        print(f'[Pipeline] An error ocurred: {e}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get all metadata from WARC files from CommonCrawl.')

    parser.add_argument('wetpaths', help="'wet.paths' file.")
    parser.add_argument('dest', help='Folder path to save content.')
    parser.add_argument('--num_responses', help='Number of responses to save per record (default is no limit).', required=False)
    parser.add_argument('--num_workers', help='Number of workers to process the pipeline (default is 1).', required=False)
    parser.add_argument('--errors_file', help='File to save which files failed while processing.', required=False)
    parser.add_argument('--without_decompression', help='Removes decompression from pipeline.', action='store_true')
    parser.add_argument('--test', help='Activates test mode. This option disables saving and only check if WARC-Refers-To fields (WET) match WARC-Record-ID in WARC files. Requires a path folder containing WARC CSV files.', required=False)

    args = parser.parse_args()

    wetpaths = args.wetpaths
    dest = args.dest
    num_responses = int(args.num_responses) if args.num_responses != None else 0
    num_workers = int(args.num_workers) if args.num_workers != None else 1
    errors_file = args.errors_file
    without_decompression = args.without_decompression
    TEST_PATH = args.test

    run_pipeline(wetpaths, dest_path=dest, errors=errors_file, max_count=num_responses,
                 num_workers=num_workers, decompression=not without_decompression)
