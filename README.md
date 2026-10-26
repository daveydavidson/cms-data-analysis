# CMS Hospitals dataset downloader

Fetches the CMS Provider Data catalog (one record per dataset), saves it as a table along with a separate 
keywords table, and downloads every dataset whose theme includes “Hospitals”. Column names are converted to 
snake_case, and each dataset is written as a CSV to output/. Designed to run daily: it stores each dataset’s 
modified date from the previous run (a per-dataset watermark) and only re-downloads datasets that are new or 
have changed.

## How to Run It
    pip install -r requirements.txt
    python cms_hospitals_download.py

## Schedule daily Example
- Linux/macOS (cron): `0 6 * * * cd /path/to/project && venv/bin/python cms_hospitals_download.py`
- Windows: Task Scheduler, daily trigger, action = path\to\venv\Scripts\python.exe with the script as argument,
  "Start in" set to the project folder.

## How it works
1. Fetch the catalog and keep records whose `theme` includes "Hospitals" (75 datasets on October 23rd, 2026).
2. Compare each dataset's `modified` date to dataset_state.json. New or different = download.
3. Download in parallel (ThreadPoolExecutor, 5 workers; the work is network-bound, so threads fit).
4. Read all columns as text (no type inference), convert headers to snake_case, write CSV.
5. Record a dataset's `modified` date in the state file only after it succeeded, so failures retry next run.

## Design decisions
- State is per dataset, not one global timestamp: a failed or partial run can't cause datasets to be skipped.
- `modified` is date-only, so I compare for inequality rather than "newer than", to avoid missing same-day updates.
- Only the main thread updates the state dictionary; workers only download and write files.
- A broad `except Exception` around each dataset is deliberate: one bad dataset must not stop the batch.

## Sample folder
The sample output folder contains three sample datasets, the console output of a full run and a repeat run, and the state file after the full run.

## Assumptions and limitations
- Each dataset’s first distribution is its CSV; confirmed by a full run in which all 75 downloaded and wrote 
  successfully. 
- No retry/backoff on downloads; a failed dataset is retried on the next scheduled run.
- Data is not type-cast; everything is written as text. Assumption is that landed data would form bronze layer of
  medallion architecture.
- catalog files (hospital_catalog.csv, dataset_keywords.csv) are by-products for inspection.
- Dataset downloads use pandas’ URL reader, which has no explicit timeout or retry; only the catalog request sets a 
  timeout.

## Testing performed
- 3-dataset run, repeat run (all skipped), edited a stored date (only that dataset re-downloaded).
- Full run: 75 datasets in 36 seconds; repeat run: 0 to download, 75 unchanged.