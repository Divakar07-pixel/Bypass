# Bulk PDF Downloader (Unlimited Wait + CAPTCHA OCR)

A Python-based Selenium automation tool for downloading Tamil Nadu Electoral Roll PDFs in bulk from the TN eRolls portal. The script automatically solves CAPTCHA images using OCR, downloads PDFs, renames files based on polling station codes, logs progress, and prevents the system from sleeping during long-running download sessions.

## Features

* Bulk PDF download from Excel input file
* Automatic CAPTCHA recognition using ddddocr
* Unlimited wait for slow downloads
* Automatic file renaming using `pt` parameter from URL
* Resume support (skips already downloaded files)
* Download speed and file size tracking
* Failure logging and retry mechanism
* Automatic Chrome download handling
* Prevents Windows sleep mode during execution
* Detailed execution logs

## Folder Structure

```text
Bypass/
│
├── Input/
│   └── pdflink.xlsx
│
├── Output/
│   └── Downloaded PDFs
│
├── Logs/
│   ├── run.log
│   ├── download_log_YYYYMMDD.csv
│   └── failed_urls_YYYYMMDD.txt
│
└── gemini.py
```

## Requirements

### Python

Python 3.10+

### Install Dependencies

```bash
pip install selenium
pip install openpyxl
pip install ddddocr
```

Or:

```bash
pip install -r requirements.txt
```

### requirements.txt

```text
selenium
openpyxl
ddddocr
```

## Chrome Requirements

Install:

* Google Chrome
* Compatible ChromeDriver

Ensure ChromeDriver is available in your system PATH or in the project directory.

## Input File Format

Create:

```text
Input/pdflink.xlsx
```

Example:

| S.No | PDF Link                                                                                       |
| ---- | ---------------------------------------------------------------------------------------------- |
| 1    | https://www.erolls.tn.gov.in/rollpdf/Verification_DR_29102024.aspx?dt=dt5&ac=ac051&pt=ac051001 |
| 2    | https://www.erolls.tn.gov.in/rollpdf/Verification_DR_29102024.aspx?dt=dt5&ac=ac051&pt=ac051002 |
| 3    | https://www.erolls.tn.gov.in/rollpdf/Verification_DR_29102024.aspx?dt=dt5&ac=ac051&pt=ac051003 |

**Important:** URLs must be stored in Column B and data should start from Row 2.

## Output Naming

The script automatically extracts the polling station code from the URL.

Example:

```text
https://...&pt=ac051001
```

Downloads as:

```text
ac051001.pdf
```

## Running the Script

```bash
python gemini.py
```

Example:

```bash
py gemini.py
```

## Logging

### Download Log

```text
Logs/download_log_YYYYMMDD.csv
```

Contains:

* Timestamp
* URL
* Filename
* Status
* File Size
* Download Time
* Download Speed

### Failed URLs

```text
Logs/failed_urls_YYYYMMDD.txt
```

Stores URLs that failed after all retry attempts.

### Runtime Log

```text
Logs/run.log
```

Stores detailed execution logs and errors.

## CAPTCHA Handling

The script:

1. Opens the PDF download page.
2. Captures CAPTCHA image.
3. Uses ddddocr to predict text.
4. Submits CAPTCHA automatically.
5. Retries if CAPTCHA is incorrect.
6. Refreshes CAPTCHA for subsequent attempts.

Default OCR retries:

```python
MAX_OCR_RETRIES = 3
```

## Download Process

### Phase 1

Waits up to 15 seconds to verify that the download has started.

### Phase 2

Once a download begins, the script waits indefinitely until:

* Download completes
* File is fully written
* File is renamed correctly

This ensures reliable downloads even on slow internet connections.

## Resume Capability

The script automatically checks:

```text
download_log_YYYYMMDD.csv
```

and skips files already downloaded successfully.

This allows safe restart after:

* System restart
* Power failure
* Internet interruption
* Manual stop

## Safety Features

* Prevents Windows sleep mode while running
* Restores normal sleep settings after completion
* Detects closed Chrome sessions and relaunches automatically
* Handles server alerts and CAPTCHA failures
* Supports long-running download batches

## Example Console Output

```text
============================================================
Bulk PDF Downloader (Unlimited Wait + Keep Awake)
Started : 2026-08-13 21:19:22
Output  : F:\Automation_Work\Bypass\Output
============================================================

Total URLs    : 100
Already done  : 20
Pending       : 80

[1/80] Processing: ac051001.pdf
OCR Attempt 1/3: Extracted '8J2K'
Download in progress...
Saved: ac051001.pdf (560 KB)

Progress: 1/80 (1.3%)
```

## Disclaimer

This project is intended for educational, research, and administrative automation purposes only. Ensure compliance with the terms of use and policies of the target website before running large-scale automated downloads.

## Author

Divakar R

Tamil Nadu Electoral Roll PDF Automation Project
