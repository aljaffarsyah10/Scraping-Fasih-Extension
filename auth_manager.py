"""
Modul Autentikasi Otomatis Fasih SM BPS
Menggunakan Playwright Persistent Context untuk:
1. Memeriksa validitas cookie sesi yang ada secara cepat.
2. Jika kedaluwarsa/belum ada, otomatis membuka browser dan mengisikan akun & kata sandi ke SSO BPS.
3. Mendukung input OTP interaktif (jika akun mengaktifkan 2FA).
4. Menyimpan cookie sesi yang baru ke fresh_cookie.txt secara otomatis.
"""

import os
import sys
import re
import time
import json
import getpass
from pathlib import Path
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / ".chrome_profile"
COOKIE_FILE = BASE_DIR / "fresh_cookie.txt"
CONFIG_FILE = BASE_DIR / "config_account.json"

DEFAULT_ENDPOINT = "https://fasih-sm.bps.go.id/app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode"
DEFAULT_SURVEY_PERIOD_ID = "fd68e454-ba45-4b85-8205-f3bf777ded24"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

def extract_xsrf_token(cookie_str):
    """Mengekstrak nilai XSRF-TOKEN dari header Cookie string"""
    if not cookie_str:
        return ""
    m = re.search(r"XSRF-TOKEN=([^;]+)", cookie_str, re.IGNORECASE)
    return m.group(1).strip() if m else ""

def test_cookie_validity(cookie_str, survey_period_id=DEFAULT_SURVEY_PERIOD_ID):
    """
    Menguji apakah cookie sesi masih aktif dan diizinkan mengakses data Fasih SM
    Mengembalikan: (is_valid: bool, status_code: int)
    """
    if not cookie_str:
        return False, 0

    xsrf = extract_xsrf_token(cookie_str)
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Origin": "https://fasih-sm.bps.go.id",
        "Referer": f"https://fasih-sm.bps.go.id/app/surveys/a0429e96-51a5-477b-a415-485f9c153004/{survey_period_id}/data",
        "User-Agent": DEFAULT_USER_AGENT,
        "X-XSRF-TOKEN": xsrf,
        "Cookie": cookie_str
    }
    payload = {
        "start": 0, "length": 1,
        "columns": [{"data": "id"}],
        "order": [],
        "search": {"value": "", "regex": False},
        "assignmentExtraParam": {
            "surveyPeriodId": survey_period_id,
            "assignmentErrorStatusType": -1,
            "filterTargetType": "TARGET_ONLY"
        }
    }
    try:
        r = requests.post(DEFAULT_ENDPOINT, json=payload, headers=headers, verify=False, timeout=8)
        if r.status_code == 200:
            return True, 200
        return False, r.status_code
    except Exception:
        return False, -1

def get_saved_credentials():
    """Membaca akun tersimpan dari config_account.json jika tersedia"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("username", ""), data.get("password", "")
        except Exception:
            pass
    return "", ""

def save_credentials(username, password):
    """Menyimpan akun ke config_account.json lokal (diabaikan oleh git)"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"username": username, "password": password}, f, indent=2)
        print("💾 Akun berhasil disimpan ke 'config_account.json' untuk login berikutnya.")
    except Exception as e:
        print(f"⚠️ Gagal menyimpan akun: {e}")

def prompt_credentials(cli_user=None, cli_pass=None):
    """Meminta input akun dan kata sandi jika belum disediakan"""
    user = cli_user or os.environ.get("FASIH_USER", "")
    pwd = cli_pass or os.environ.get("FASIH_PASS", "")

    if not user or not pwd:
        saved_u, saved_p = get_saved_credentials()
        if not user:
            user = saved_u
        if not pwd:
            pwd = saved_p

    if not user:
        print("\n" + "=" * 60)
        print("🔐 AUTENTIKASI AKUN SSO BPS (PORTAL FASIH SM)")
        print("=" * 60)
        user = input("👉 Masukkan Akun / Username SSO BPS: ").strip()

    if not pwd:
        pwd = getpass.getpass("👉 Masukkan Kata Sandi (Password): ").strip()

    return user, pwd

def run_browser_login(username, password, headless=False):
    """
    Meluncurkan browser otomatis, mengisi form SSO BPS, dan mengekstrak cookie sesi baru
    """
    from playwright.sync_api import sync_playwright

    print("\n🌐 Membuka peramban untuk verifikasi sesi SSO BPS...")
    PROFILE_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        args = [
            "--disable-blink-features=AutomationControlled",
            "--start-maximized",
            "--no-sandbox"
        ]

        # Gunakan persistent context agar cache & security challenge tersimpan
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=headless,
            no_viewport=True,
            locale="id-ID",
            args=args
        )

        page = context.pages[0] if context.pages else context.new_page()

        print("📍 Mengarahkan ke https://fasih-sm.bps.go.id/app/ ...")
        try:
            page.goto("https://fasih-sm.bps.go.id/app/", timeout=45000)
        except Exception as e:
            print(f"⚠️ Catatan navigasi: {e}")

        print("⏳ Menunggu deteksi sesi login...")
        is_logged_in = False
        start_time = time.time()
        timeout_seconds = 120

        while time.time() - start_time < timeout_seconds:
            time.sleep(1.5)
            curr_url = page.url

            # Kasus A: Halaman berada di SSO BPS (sso.bps.go.id)
            if "sso.bps.go.id" in curr_url:
                try:
                    user_input = page.locator('#username, input[name="username"]')
                    pass_input = page.locator('#password, input[name="password"]')
                    login_btn = page.locator('#kc-login, input[type="submit"], button[type="submit"]')

                    if user_input.is_visible(timeout=1000) and pass_input.is_visible(timeout=1000):
                        print("🔑 Mengisikan username dan password ke form SSO...")
                        user_input.fill(username)
                        pass_input.fill(password)
                        time.sleep(0.5)
                        login_btn.click()
                        print("🚀 Tombol Login ditekan. Menunggu pengalihan ke Fasih...")
                        time.sleep(3)
                        continue

                    # Cek jika ada verifikasi OTP / 2FA
                    otp_input = page.locator('#otp, input[name="otp"], input[autocomplete="one-time-code"]')
                    if otp_input.is_visible(timeout=1000):
                        print("\n⚠️ PERHATIAN: Halaman verifikasi OTP / 2FA terdeteksi!")
                        print("👉 Silakan masukkan kode OTP Anda langsung di jendela Chrome yang terbuka...")
                        # Tunggu sampai berpindah dari halaman OTP
                        while "sso.bps.go.id" in page.url and time.time() - start_time < timeout_seconds:
                            time.sleep(1)
                except Exception:
                    pass

            # Kasus B: Berhasil masuk ke portal Fasih SM
            if "fasih-sm.bps.go.id/app" in curr_url and "login" not in curr_url.lower():
                cookies = context.cookies()
                cookie_names = [c["name"] for c in cookies]
                if any("SESSION" in n or "JSESSIONID" in n for n in cookie_names):
                    print("🎉 Berhasil masuk ke portal Fasih SM!")
                    is_logged_in = True
                    break

        if not is_logged_in:
            # Cek final pada daftar cookies
            cookies = context.cookies()
            cookie_names = [c["name"] for c in cookies]
            if any("SESSION" in n or "JSESSIONID" in n for n in cookie_names):
                is_logged_in = True

        if not is_logged_in:
            print("❌ Gagal login atau batas waktu tunggu habis.")
            context.close()
            return None, None

        # Beri jeda 2 detik agar seluruh token terisi lengkap
        time.sleep(2)
        cookies = context.cookies()
        cookie_parts = []
        xsrf_token = ""

        for c in cookies:
            cookie_parts.append(f"{c['name']}={c['value']}")
            if c['name'].upper() == 'XSRF-TOKEN':
                xsrf_token = c['value']

        full_cookie_str = "; ".join(cookie_parts)

        # Simpan ke fresh_cookie.txt
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            f.write(full_cookie_str)

        print("✅ Cookie sesi terbaru berhasil diekstrak dan disimpan ke 'fresh_cookie.txt'!")
        context.close()
        return full_cookie_str, xsrf_token

def get_valid_cookie(cli_user=None, cli_pass=None, survey_period_id=DEFAULT_SURVEY_PERIOD_ID, force_login=False, save_account=False):
    """
    Fungsi utama:
    1. Cek apakah fresh_cookie.txt sudah ada dan masih aktif.
    2. Jika aktif dan tidak force_login, langsung gunakan (tanpa buka browser!).
    3. Jika tidak aktif, minta akun & kata sandi, lalu lakukan auto-login via browser.
    """
    # 1. Cek file cookie yang ada
    current_cookie = ""
    if COOKIE_FILE.exists() and not force_login:
        try:
            with open(COOKIE_FILE, "r", encoding="utf-8") as f:
                current_cookie = f.read().strip()
        except Exception:
            current_cookie = ""

    if current_cookie and not force_login:
        print("🔍 Memeriksa validitas cookie sesi yang tersimpan...", end="", flush=True)
        is_valid, status = test_cookie_validity(current_cookie, survey_period_id)
        if is_valid:
            print(" [AKTIF & VALID]")
            xsrf = extract_xsrf_token(current_cookie)
            return current_cookie, xsrf
        else:
            print(f" [KEDALUWARSA / HTTP {status}]")

    # 2. Jika tidak valid, jalankan auto login
    print("⚡ Memulai proses login otomatis SSO BPS...")
    user, pwd = prompt_credentials(cli_user, cli_pass)
    if not user or not pwd:
        print("❌ Login dibatalkan: akun atau kata sandi tidak diisi.")
        return None, None

    cookie_str, xsrf = run_browser_login(user, pwd)

    if cookie_str and save_account:
        save_credentials(user, pwd)

    return cookie_str, xsrf

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Autentikasi Otomatis Fasih SM BPS")
    parser.add_argument("-u", "--username", help="Username SSO BPS")
    parser.add_argument("-p", "--password", help="Password SSO BPS")
    parser.add_argument("--save", action="store_true", help="Simpan kredensial ke config_account.json")
    parser.add_argument("--force", action="store_true", help="Paksa login ulang meskipun cookie masih ada")
    args = parser.parse_args()

    c, x = get_valid_cookie(
        cli_user=args.username,
        cli_pass=args.password,
        force_login=args.force,
        save_account=args.save
    )

    if c:
        print("\n✨ Siap digunakan untuk scraping data Fasih SM!")
    else:
        sys.exit(1)
