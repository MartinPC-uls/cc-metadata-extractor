import pandas as pd
import os
import argparse
import threading
from utils import *
from itertools import islice
from warcio.archiveiterator import ArchiveIterator

def get_metadata(warc_path, max_count=0, remove=False):
    warc = warc_path.split('.')[0].split('/')[-1] # second split in case that is a folder path

    i = 0
    records = []
    with open(warc_path, 'rb') as stream:
        for record in ArchiveIterator(stream):
            if i >= max_count and max_count != 0: break
            if record.rec_type == 'response':
                warc_record_id = record.rec_headers.get_header('WARC-Record-ID')
                warc_target_uri = record.rec_headers.get_header('WARC-Target-URI')
                content_language = record.http_headers.get_header('Content-Language')
                
                content = record.content_stream().read()
                records.append({
                    'WARC-File': warc,
                    'WARC-Record-ID': warc_record_id,
                    'WARC-Target-URI': warc_target_uri,
                    'Domain': get_domain_from_url(warc_target_uri).split('.')[-1],
                    'Language': extract_lang(content) if content_language is None else content_language
                })

                i += 1
        
    if remove:
        os.remove(warc_path)

    return records

def save_metadata(dest: str, records: list):
    df = pd.DataFrame(records)

    df.to_csv(dest, index=False)

def process(path, dest_path, errors, max_count):
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
