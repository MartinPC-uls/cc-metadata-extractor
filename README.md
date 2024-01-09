# cc-metadata-extractor
This is a Metadata Extractor for CENIA (Centro Nacional de Inteligencia Artificial).

# What does it extract?
It extracts the following info from WARC records in CommonCrawl (CC):
- **WARC-File**: Indicates in which file the record was found.
- **WARC-Record-ID**: Indicates the Record ID. Using **WET** format we can extract the content of this record by searching in **WARC-Refers-To** field.
- **WARC-Target-URI**: Indicates the URL from where the record was extracted.
- **Domain**: Indicates a single domain of the URL where the record was extracted from.
- **Content-Language**: Indicates the language found for the record in the HTTP response.
- **HTML-Language**: Indicates the language found for the record in the HTML tags (either 'lang' or 'xml:lang').
- **HTML-Dir**: Indicates the text direction of the text found in the HTML 'dir' tag.

# How it works
It extracts the metadata found in every WARC record response and saves it in CSV files (per WARC path) with the fields indicated in the section above.

# Usage
To run the extractor pipeline, we can look at the following command format:
~~~
python extract_metadata.py <warcpaths> <dest> [--num_responses, --num_workers, --errors_file]
~~~

- **warcpaths** (REQUIRED): 'warc.paths' file extracted from https://data.commoncrawl.org/crawl-data/CC-MAIN-2023-50/index.html (or any other crawl-data version)
- **dest** (REQUIRED): Path destination to process and save everything.
- **num_responses**: Number of responses to get from a single WARC path (by default, there is no limit).
- **num_workers**: Number of workers to execute the extraction pipeline (default is 1).
- **errors_file**: File to save the failed WARC paths.

The following example contains a command to extract 100 responses from every WARC record found in 'warc.paths'. It runs with 4 workers (threads), and it saves the failed records in a file called 'errors.txt'. All CSV files will be saved in a folder called 'dest':
~~~
python extract_metadata.py warc.paths dest --num_responses 100 --num_workers 4 --errors_file errors.txt
~~~


'test.ipynb' contains an example on how to access the generated metadata in a CSV file.
