import sys
import time
import csv
import os
import logging
import ctypes
import openpyxl
import ddddocr

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE_DIR   = Path(r"F:\Automation_Work\Bypass")
INPUT_DIR  = BASE_DIR / "Input"
OUTPUT_DIR = BASE_DIR / "Output"
LOG_DIR    = BASE_DIR / "Logs"

EXCEL_FILE  = INPUT_DIR / "pdflink.xlsx"
LOG_FILE    = LOG_DIR / f"download_log_{datetime.now().strftime('%Y%m%d')}.csv"
FAILED_FILE = LOG_DIR / f"failed_urls_{datetime.now().strftime('%Y%m%d')}.txt"

# Auto-create folders
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
CAPTCHA_INPUT_NAME = "txt_Vcode"
CAPTCHA_IMG_ID     = "Image2"
SUBMIT_BTN_ID      = "btn_Login"
REFRESH_BTN_ID     = "img_refresh"
START_TIMEOUT      = 15    # Max seconds to wait for download to START (.crdownload to appear)
MAX_OCR_RETRIES    = 3     # Retry attempts per URL if OCR fails

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "run.log", encoding="utf-8")
    ]
)
log = logging.getLogger(__name__)

# Initialize OCR Engine
ocr_engine = ddddocr.DdddOcr(show_ad=False)


# ─────────────────────────────────────────────
# SLEEP MANAGEMENT HELPERS
# ─────────────────────────────────────────────

def prevent_sleep():
    """Prevents Windows from entering sleep mode or turning off the screen."""
    if os.name == "nt":  # Check if Windows OS
        try:
            # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000002)
            log.info("⚡ Windows sleep mode disabled while script runs.")
        except Exception as e:
            log.warning(f"Could not disable sleep mode: {e}")

def allow_sleep():
    """Restores default Windows sleep settings."""
    if os.name == "nt":
        try:
            # ES_CONTINUOUS (resets to default)
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            log.info("💤 Windows sleep settings restored.")
        except Exception as e:
            log.warning(f"Could not restore sleep state: {e}")


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_filename_from_url(url: str) -> str:
    try:
        params = parse_qs(urlparse(url).query)
        pt = params.get("pt", [""])[0].strip()
        if pt:
            return f"{pt}.pdf"
        return f"download_{int(time.time())}.pdf"
    except Exception:
        return f"download_{int(time.time())}.pdf"


def load_urls_from_excel(path: Path) -> list:
    urls = []
    try:
        wb = openpyxl.load_workbook(path)
        ws = wb.active
        for row in ws.iter_rows(min_row=2, min_col=2, max_col=2, values_only=True):
            val = row[0]
            if val and str(val).startswith("http"):
                urls.append(str(val).strip())
        log.info(f"Loaded {len(urls)} URLs from {path.name}")
    except Exception as e:
        log.error(f"Failed to read Excel: {e}")
        sys.exit(1)
    return urls


def load_already_downloaded() -> set:
    done = set()
    if LOG_FILE.exists():
        with open(LOG_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("status") == "SUCCESS":
                    done.add(row.get("filename", ""))
    return done


def write_log(url: str, filename: str, status: str, size_kb: float = 0, elapsed_sec: float = 0, speed_str: str = "N/A", note: str = ""):
    file_exists = LOG_FILE.exists()
    fieldnames = ["timestamp", "url", "filename", "status", "size_kb", "elapsed_sec", "speed", "note"]
    
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "url": url,
            "filename": filename,
            "status": status,
            "size_kb": f"{size_kb:.2f}",
            "elapsed_sec": f"{elapsed_sec:.2f}",
            "speed": speed_str,
            "note": note
        })


def write_failed(url: str):
    with open(FAILED_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")


def dismiss_alert(driver) -> str:
    try:
        alert = driver.switch_to.alert
        text = alert.text
        alert.accept()
        return text
    except Exception:
        return ""


def wait_for_download_unlimited(before_files: set, correct_name: str, start_time: float):
    """
    Two-Phase Download Tracker:
    Phase 1: Quick check (15s) to confirm download actually started (.crdownload file created).
    Phase 2: Unlimited wait for slow networks until download completely finishes.
    """
    target_path = OUTPUT_DIR / correct_name
    
    # PHASE 1: Wait up to 15s to see if a download started
    start_deadline = time.time() + START_TIMEOUT
    download_started = False

    while time.time() < start_deadline:
        current_files = set(OUTPUT_DIR.glob("*"))
        new_files = current_files - before_files

        active_downloads = [f for f in new_files if f.suffix == ".crdownload"]
        completed_downloads = [f for f in new_files if f.suffix != ".crdownload" and f.name != correct_name]

        if active_downloads or completed_downloads:
            download_started = True
            break
        time.sleep(0.5)

    if not download_started:
        # Download never initiated (likely wrong CAPTCHA or server issue)
        return False, 0, 0, "0 KB/s"

    # PHASE 2: Download detected! Wait indefinitely until finished
    print("  ⏳ Download in progress... waiting until 100% complete (no time limit)...")
    
    while True:
        current_files = set(OUTPUT_DIR.glob("*"))
        new_files = current_files - before_files

        active_downloads = [f for f in new_files if f.suffix == ".crdownload"]
        completed_downloads = [f for f in new_files if f.suffix != ".crdownload" and f.name != correct_name]

        # Still downloading? Keep looping without timeout
        if active_downloads:
            time.sleep(1)
            continue

        # File completed!
        if completed_downloads:
            downloaded_file = completed_downloads[0]

            try:
                # Ensure write operations have finished
                size_before = downloaded_file.stat().st_size
                time.sleep(0.8)
                size_after = downloaded_file.stat().st_size

                if size_before == size_after and size_after > 0:
                    end_time = time.perf_counter()
                    elapsed_sec = max(end_time - start_time, 0.1)

                    if target_path.exists():
                        target_path.unlink()
                    downloaded_file.rename(target_path)

                    file_size_bytes = target_path.stat().st_size
                    size_kb = file_size_bytes / 1024
                    speed_kbps = size_kb / elapsed_sec

                    speed_str = f"{speed_kbps / 1024:.2f} MB/s" if speed_kbps >= 1024 else f"{speed_kbps:.2f} KB/s"

                    print(f"  📁 Saved: {correct_name} ({size_kb:.1f} KB) | ⚡ Time: {elapsed_sec:.2f}s | Speed: {speed_str}")
                    return True, size_kb, elapsed_sec, speed_str

            except FileNotFoundError:
                time.sleep(0.5)
                continue
            except Exception as e:
                log.warning(f"  Rename error: {e}")

        time.sleep(0.5)


# ─────────────────────────────────────────────
# CHROME SETUP
# ─────────────────────────────────────────────

def create_driver() -> webdriver.Chrome:
    output_abs = str(OUTPUT_DIR.resolve())
    if not output_abs[1:3] == ":\\":
        output_abs = os.path.abspath(str(OUTPUT_DIR))

    options = Options()
    prefs = {
        "download.default_directory": output_abs,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled": True,
        "profile.default_content_settings.popups": 0,
        "profile.default_content_setting_values.automatic_downloads": 1,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1100, 700)
    return driver


def is_session_alive(driver) -> bool:
    try:
        _ = driver.current_url
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────
# AUTOMATED CAPTCHA PROCESSING
# ─────────────────────────────────────────────

def process_url_with_ocr(driver, url: str, filename: str):
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, CAPTCHA_IMG_ID))
        )
        time.sleep(0.5)
    except Exception as e:
        log.warning(f"  Page load error: {e}")
        return False, 0, 0, "0 KB/s"

    for attempt in range(1, MAX_OCR_RETRIES + 1):
        try:
            captcha_element = driver.find_element(By.ID, CAPTCHA_IMG_ID)
            captcha_bytes = captcha_element.screenshot_as_png

            captcha_text = ocr_engine.classification(captcha_bytes).strip()
            print(f"  🤖 OCR Attempt {attempt}/{MAX_OCR_RETRIES}: Extracted '{captcha_text}'")

            if not captcha_text:
                raise ValueError("OCR returned empty text")

            before_files = set(OUTPUT_DIR.glob("*"))

            inp = driver.find_element(By.NAME, CAPTCHA_INPUT_NAME)
            inp.clear()
            inp.send_keys(captcha_text)
            time.sleep(0.2)
            
            start_time = time.perf_counter()
            driver.find_element(By.ID, SUBMIT_BTN_ID).click()

        except UnexpectedAlertPresentException:
            pass
        except Exception as e:
            log.warning(f"  Error during processing: {e}")

        time.sleep(0.8)
        alert_text = dismiss_alert(driver)
        if alert_text:
            print(f"  ❌ Server alert: {alert_text}")
            try:
                driver.find_element(By.ID, REFRESH_BTN_ID).click()
                time.sleep(1)
            except Exception:
                pass
            continue

        # Execute Unlimited Wait logic
        success, size_kb, elapsed_sec, speed_str = wait_for_download_unlimited(
            before_files, filename, start_time
        )
        
        if success:
            return True, size_kb, elapsed_sec, speed_str

        # If download didn't start, refresh captcha for next retry
        try:
            driver.find_element(By.ID, REFRESH_BTN_ID).click()
            time.sleep(1)
        except Exception:
            break

    log.warning(f"  Failed after {MAX_OCR_RETRIES} attempts.")
    return False, 0, 0, "0 KB/s"


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("   Bulk PDF Downloader (Unlimited Wait + Keep Awake)")
    print(f"   Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Output  : {OUTPUT_DIR.resolve()}")
    print("=" * 60)

    urls = load_urls_from_excel(EXCEL_FILE)
    if not urls:
        log.error("No URLs found in Excel file. Exiting.")
        sys.exit(1)

    already_done = load_already_downloaded()
    pending = [u for u in urls if get_filename_from_url(u) not in already_done]

    total   = len(pending)
    skipped = len(urls) - total

    print(f"  📋 Total URLs    : {len(urls)}")
    print(f"  ✅ Already done  : {skipped}")
    print(f"  ⏳ Pending       : {total}\n")

    if total == 0:
        print("  ✅ All files already downloaded!")
        return

    # Disable Windows sleep mode during download process
    prevent_sleep()

    driver = create_driver()
    success_count = 0
    fail_count    = 0

    try:
        for i, url in enumerate(pending, 1):
            filename = get_filename_from_url(url)
            print(f"{'─' * 55}")
            print(f"  [{i}/{total}] Processing: {filename}")

            if not is_session_alive(driver):
                log.warning("  Chrome session closed — restarting driver...")
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = create_driver()

            success, size_kb, elapsed_sec, speed_str = process_url_with_ocr(driver, url, filename)

            if success:
                write_log(url, filename, "SUCCESS", size_kb, elapsed_sec, speed_str)
                success_count += 1
            else:
                write_log(url, filename, "FAILED", 0, 0, "0 KB/s", "OCR failed or download didn't start")
                write_failed(url)
                fail_count += 1

            pct = round((i / total) * 100, 1)
            print(f"  Progress: {i}/{total} ({pct}%)  ✅ {success_count}  ❌ {fail_count}")

    except KeyboardInterrupt:
        log.warning("\n⚠️ Stopped by user. Progress recorded.")

    finally:
        # Restore normal sleep settings upon exit or completion
        allow_sleep()
        try:
            driver.quit()
        except Exception:
            pass

    print("=" * 60)
    print(f"  COMPLETE!  ✅ Success: {success_count} | ❌ Failed: {fail_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()