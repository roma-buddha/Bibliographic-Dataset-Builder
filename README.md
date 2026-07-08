# Bibliographic Dataset Builder

A static browser app for building bibliographic datasets from OpenAlex, Web of Science, and Scopus exports.

## Files

- `index.html` - main GitHub Pages entry point.
- `bibliographic_dataset_builder.html` - named copy of the app.
- `openalex_extraction_reference.py` - original OpenAlex notebook-style code reference.

## Features

- Extract records from OpenAlex.
- Merge and deduplicate Web of Science tab-delimited files.
- Convert Scopus CSV exports into WoS-style tab-delimited data.
- Merge converted source files, track source database overlap, and export final TSV/CSV files.

The app runs entirely in the browser. Uploaded files are processed locally and are not sent to a server.
