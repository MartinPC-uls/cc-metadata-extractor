import pandas as pd
import os
import operator
from utils import *
from fastwarc.warc import ArchiveIterator

def _get_paths(paths_file: str) -> dict:
    if not os.path.exists(paths_file): return {}

    _dict = {}
    _type = paths_file.split('/')[-1].split('\\')[-1].split('.')[0]

    suffix = ''
    if _type == 'warc':
        suffix = '.warc.gz'
    elif _type == 'wet':
        suffix = '.warc.wet.gz'

    paths = open(paths_file, 'r').read().splitlines()
    for path in paths:
        segments = path.split('/')
        crawl_data = f'{segments[0]}/{segments[1]}/'
        segment = f'{segments[2]}/{segments[3]}/{segments[4]}/'

        prefix = crawl_data + segment

        file = segments[5].removesuffix(suffix)
        _dict[file] = prefix

    return _dict

wet_dict = _get_paths('wet.paths')

comparison_func = {
    '==': operator.eq,
    '!=': operator.ne,
    'in': operator.contains
}

class WARCChunk:
    def __init__(self, csv_warc_chunk: str, ignore_errors=False):
        self.chunk = csv_warc_chunk
        self.chunk_name = csv_warc_chunk.split('/')[-1].split('\\')[-1].removesuffix('.csv')
        self.warc_df = pd.read_csv(self.chunk, index_col='WARC_Record_ID')
        self.ignore_errors = ignore_errors
        self.wet_df = None
        self._load()

    def _load(self):
        if self.chunk_name not in wet_dict and not self.ignore_errors:
            raise f'{self.chunk_name} does not exist in wet.paths'
        
        prefix = wet_dict[self.chunk_name]
        file = f'{self.chunk_name}.warc.wet.gz'
        dest_file = prefix+file
        download(dest_file, '.')

        records = []
        with open(file, 'rb') as stream:
            for record in ArchiveIterator(stream):
                content_type = get_warc_header('Content_Type', record.headers)
                if not content_type: continue
                if content_type != 'text/plain': continue

                warc_refers_to = get_warc_header('WARC_Refers_To', record.headers)
                content = record.reader.read().decode('utf-8', errors='replace')

                records.append({
                    'WARC_Refers_To': warc_refers_to,
                    'Content': content
                })

        self.wet_df = pd.DataFrame(records)
        self.wet_df.set_index('WARC_Refers_To', inplace=True)

        os.remove(file)
    
    def get_text(self, warc_record_id, default_value='') -> str:
        try:
            return self.wet_df.at[warc_record_id, 'Content']
        except KeyError:
            if not self.ignore_errors:
                raise f'{warc_record_id} does not exist in the WET format.'

            return default_value
        
    def get_metadata(self, warc_record_id, column, default_value='') -> str:
        try:
            return self.warc_df.at[warc_record_id, column]
        except KeyError:
            if not self.ignore_errors:
                raise f'{warc_record_id} does not exist in the WARC format'
            
            return default_value
        
    def get(self, query=None, frac=1) -> list:
        if query is None:
            return self.warc_df.sample(frac=frac).index.tolist()
        
        return self.warc_df.query(query).sample(frac=frac).index.tolist()
    
    def save(self, dest_folder = '.', query=None, sample=1, filters=None):
        dest = f'{dest_folder}/{self.chunk_name}.csv'

        records = self.get(query, sample)

        data = []
        for record in records:
            if filters is not None and not all(f(record) for f in filters):
                continue

            data.append({
                'WARC_File': self.chunk_name,
                'WARC_Record_ID': record,
                'Text': self.get_text(record),
                'WARC_Target_URI': self.get_metadata(record, 'WARC_Target_URI'),
                'Content_Language': self.get_metadata(record, 'Content_Language'),
                'HTML_Lang': self.get_metadata(record, 'HTML_Lang'),
                'HTML_Dir': self.get_metadata(record, 'HTML_Dir'),
                'Domain': self.get_metadata(record, 'Domain')
            })
            
        df = pd.DataFrame(data)
        df.to_csv(dest, index=False)

    def filter_metadata(self, record, metadata, target, operator_type='=='):
        comparison_func.get(operator_type)

        if comparison_func is None:
            raise ValueError("Invalid operator_type. Supported values are '==', '!=' and 'in'.")

        _metadata = self.get_metadata(record, metadata)
        return comparison_func(target, _metadata)
    
    
    def filter_text(self, record, target, operator_type='==', sensitive=True):
        comparison_func.get(operator_type)

        if comparison_func is None:
            raise ValueError("Invalid operator_type. Supported values are '==', '!=' and 'in'.")
        
        text = self.get_text(record)

        if sensitive:
            return comparison_func(target, text)
                    
        return comparison_func(target.lower(), text.lower())
        
