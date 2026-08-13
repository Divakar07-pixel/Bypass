# Bulk PDF Downloader

Python-based automation tool developed for internal operational use to download Electoral Roll PDF documents in bulk, automatically solve CAPTCHA challenges using OCR, manage downloads, and generate execution logs.

## Overview

This application automates the process of:

* Reading PDF URLs from an Excel file
* Opening each URL in Chrome using Selenium
* Solving CAPTCHA images using OCR
* Downloading PDF files automatically
* Renaming files based on polling station codes
* Recording download status and performance metrics
* Supporting resume functionality for interrupted runs
* Preventing system sleep during long download sessions

## Features

### Automated Processing

* Bulk URL processing from Excel
* CAPTCHA recognition using ddddocr
* Automatic PDF download
* Automatic file naming
* Automatic retry mechanism

### Download Management

* Unlimited wait for slow downloads
* Download progress tracking
* Resume capability
* Failed URL tracking
* Automatic Chrome session recovery

### Monitoring & Logging

* Runtime logs
* Download history logs
* Success and failure statistics
* Download speed monitoring
* File size tracking

## Project Structure

```text
Bypass/
│
├── Input/
│   └── pdflink.xlsx
│
├── Output/
│   └── Downloaded PDF Files
│
├── Logs/
│   ├── run.log
│   ├── download_log_YYYYMMDD.csv
│   └── failed_urls_YYYYMMDD.txt
│
└── gemini.py
```

## Technology Stack

* Python
* Selenium WebDriver
* Google Chrome
* OpenPyXL
* ddddocr
* CSV Logging
* Windows Power Management APIs

## Prerequisites

### Python

Python 3.10 or later

### Required Packages

```bash
pip install selenium
pip install openpyxl
pip install ddddocr
```

Or install using:

```bash
pip install -r requirements.txt
```

### requirements.txt

```text
selenium
openpyxl
ddddocr
```

## Input File Format

Create the file:

```text
Input/pdflink.xlsx
```

Example:

| S.No | PDF Link                  |
| ---- | ------------------------- |
| 1    | https://example.com/link1 |
| 2    | https://example.com/link2 |
| 3    | https://example.com/link3 |

### Important

* URLs should be placed in Column B.
* Data should start from Row 2.
* Row 1 should contain headers.

## Output

Downloaded files are saved to:

```text
Output/
```

Files are automatically named based on the polling station code extracted from the URL.

Example:

```text
ac051001.pdf
ac051002.pdf
ac051003.pdf
```

## Execution

Run the script:

```bash
python gemini.py
```

or

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
* Download Duration
* Download Speed
* Notes

### Failed URL Log

```text
Logs/failed_urls_YYYYMMDD.txt
```

Stores URLs that could not be processed successfully.

### Runtime Log

```text
Logs/run.log
```

Contains application events, warnings, and error messages.

## CAPTCHA Processing

The application uses OCR technology to:

1. Capture CAPTCHA image.
2. Extract text automatically.
3. Submit CAPTCHA.
4. Retry when validation fails.
5. Refresh CAPTCHA when required.

## Resume Support

Previously downloaded files are identified from the log history and skipped automatically during subsequent runs.

This allows safe recovery after:

* Network interruptions
* System restart
* Application restart
* Manual termination

## Security & Usage

This application is intended solely for authorized operational use.

Users are responsible for ensuring compliance with applicable organizational policies, operational procedures, and system access requirements before executing the automation.

## Confidentiality Notice

This repository contains software developed for internal business operations.

The source code, documentation, workflows, and implementation details may contain operational knowledge intended for authorized personnel only.

Do not distribute, publish, or disclose any portion of this repository externally without appropriate approval from the organization.

## Maintenance

For issue reporting, enhancements, or operational support, contact the project owner or designated maintenance team.

## Author

Divakar R

Operations Automation Project
