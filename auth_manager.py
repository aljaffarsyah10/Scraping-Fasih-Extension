"""
Modul Autentikasi Otomatis Fasih SM BPS (Dengan Dukungan Akun, Sandi, dan OTP / 2FA)
Menggunakan Playwright Persistent Context untuk:
1. Memeriksa validitas cookie sesi yang ada secara cepat.
2. Jika kedaluwarsa/belum ada, otomatis membuka peramban dan mengisikan akun & kata sandi ke SSO BPS.
3. Mendukung verifikasi 2FA / OTP:
   - Auto-Generate 100% jika memiliki OTP Secret Key (Base32 via pyotp).
   - Input langsung 6 digit kode OTP via CLI / terminal.
   - Pengisian langsung interaktif di jendela peramban.
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
                return (
                    data.get("username", ""),
                    data.get("password", ""),
                    data.get("otp_secret", "")
                )
        except Exception:
            pass
    return "", "", ""

def save_credentials(username, password, otp_secret=""):
    """Menyimpan akun ke config_account.json lokal (diabaikan oleh git)"""
    try:
        payload = {"username": username, "password": password}
        if otp_secret:
            payload["otp_secret"] = otp_secret
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print("💾 Kredensial akun berhasil disimpan ke 'config_account.json' untuk login berikutnya.")
    except Exception as e:
        print(f"⚠️ Gagal menyimpan akun: {e}")

def prompt_credentials(cli_user=None, cli_pass=None, cli_otp_secret=None):
    """Meminta input akun dan kata sandi jika belum disediakan"""
    saved_u, saved_p, saved_otp_secret = get_saved_credentials()

    user = cli_user or os.environ.get("FASIH_USER", "") or saved_u
    pwd = cli_pass or os.environ.get("FASIH_PASS", "") or saved_p
    otp_sec = cli_otp_secret or os.environ.get("FASIH_OTP_SECRET", "") or saved_otp_secret

    if not user:
        print("\n" + "=" * 60)
        print("🔐 AUTENTIKASI AKUN SSO BPS (PORTAL FASIH SM)")
        print("=" * 60)
        user = input("👉 Masukkan Akun / Username SSO BPS: ").strip()

    if not pwd:
        pwd = getpass.getpass("👉 Masukkan Kata Sandi (Password): ").strip()

    return user, pwd, otp_sec

def generate_totp_code(secret_key):
    """Generate 6-digit TOTP code dari Base32 Secret Key menggunakan pyotp"""
    try:
        import pyotp
        clean_secret = secret_key.replace(" ", "").strip().upper()
        totp = pyotp.TOTP(clean_secret)
        return totp.now()
    except Exception as e:
        print(f"⚠️ Gagal menghasilkan kode TOTP otomatis: {e}")
        return ""

def run_browser_login(username, password, otp_secret="", cli_otp="", headless=False):
    """
    Meluncurkan peramban otomatis, mengisi form SSO BPS, menangani OTP, dan mengekstrak cookie sesi baru
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
        otp_prompted = False

        while time.time() - start_time < timeout_seconds:
            time.sleep(1.5)
            curr_url = page.url

            # Kasus A: Halaman berada di SSO BPS (sso.bps.go.id)
            if "sso.bps.go.id" in curr_url:
                try:
                    # 1. Tahap Username & Password
                    user_input = page.locator('#username, input[name="username"]')
                    pass_input = page.locator('#password, input[name="password"]')
                    login_btn = page.locator('#kc-login, input[type="submit"], button[type="submit"]')

                    if user_input.is_visible(timeout=1000) and pass_input.is_visible(timeout=1000):
                        print("🔑 Mengisikan username dan password ke form SSO...")
                        user_input.fill(username)
                        pass_input.fill(password)
                        time.sleep(0.5)
                        login_btn.click()
                        print("🚀 Tombol Login ditekan. Menunggu verifikasi...")
                        time.sleep(3)
                        continue

                    # 2. Tahap Verifikasi OTP / 2FA
                    otp_input = page.locator('#otp, input[name="otp"], input[autocomplete="one-time-code"], input[name="totp"]')
                    if otp_input.is_visible(timeout=1000):
                        otp_submit_btn = page.locator('#kc-login, input[type="submit"], button[type="submit"]')

                        # Cara 1: Auto-generate dari OTP Secret (jika ada)
                        if otp_secret:
                            auto_code = generate_totp_code(otp_secret)
                            if auto_code:
                                print(f"\n🔐 Menghasilkan kode OTP otomatis dari secret key: {auto_code}")
                                otp_input.fill(auto_code)
                                time.sleep(0.5)
                                otp_submit_btn.click()
                                print("🚀 Kode OTP otomatis telah dikirim. Menunggu pengalihan...")
                                time.sleep(3)
                                continue

                        # Cara 2: Dari argumen CLI (--otp 123456)
                        if cli_otp:
                            print(f"\n🔑 Mengisikan kode OTP yang diberikan: {cli_otp}")
                            otp_input.fill(cli_otp)
                            time.sleep(0.5)
                            otp_submit_btn.click()
                            print("🚀 Kode OTP telah dikirim. Menunggu pengalihan...")
                            cli_otp = "" # Cegah re-submit
                            time.sleep(3)
                            continue

                        # Cara 3: Meminta input langsung di terminal
                        if not otp_prompted:
                            otp_prompted = True
                            print("\n" + "=" * 60)
                            print("⚠️ TERDETEKSI HALAMAN VERIFIKASI 2FA / OTP DI SSO BPS!")
                            print("=" * 60)
                            print("👉 Buka aplikasi Google Authenticator / FreeOTP di HP Anda.")
                            user_otp = input("👉 Masukkan 6 Digit Kode OTP: ").strip()
                            if user_otp:
                                otp_input.fill(user_otp)
                                time.sleep(0.5)
                                otp_submit_btn.click()
                                print("🚀 Kode OTP dikirim. Menunggu verifikasi...")
                                time.sleep(3)
                                continue
                            else:
                                print("ℹ️ Anda juga dapat mengisi kode OTP langsung di jendela Chrome yang terbuka.")

                        # Tunggu pengguna menyelesaikan di browser jika input di terminal dilewati
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

        print("\n" + "=" * 60)
        print("✅ COOKIE SESI TERBARU BERHASIL DISIMPAN KE 'fresh_cookie.txt'!")
        print("=" * 60)

        context.close()
        return full_cookie_str, xsrf_token

def get_valid_cookie(cli_user=None, cli_pass=None, cli_otp_secret=None, cli_otp="", survey_period_id=DEFAULT_SURVEY_PERIOD_ID, force_login=False, save_account=False):
    """
    Fungsi utama:
    1. Cek apakah fresh_cookie.txt sudah ada dan masih aktif.
    2. Jika aktif dan tidak force_login, langsung gunakan (tanpa buka browser!).
    3. Jika tidak aktif, minta akun, kata sandi, dan OTP, lalu lakukan auto-login via browser.
    """
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

    print("⚡ Memulai proses login otomatis SSO BPS...")
    user, pwd, otp_sec = prompt_credentials(cli_user, cli_pass, cli_otp_secret)
    if not user or not pwd:
        print("❌ Login dibatalkan: akun atau kata sandi tidak diisi.")
        return None, None

    cookie_str, xsrf = run_browser_login(
        username=user,
        password=pwd,
        otp_secret=otp_sec,
        cli_otp=cli_otp
    )

    if cookie_str and save_account:
        save_credentials(user, pwd, otp_sec)

    return cookie_str, xsrf

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Autentikasi Otomatis Fasih SM BPS (Dengan Dukungan OTP)")
    parser.add_argument("-u", "--username", help="Username SSO BPS")
    parser.add_argument("-p", "--password", help="Password SSO BPS")
    parser.add_argument("--otp", help="6 Digit Kode OTP langsung (Opsional)", default="")
    parser.add_argument("--otp-secret", help="Secret Key Base32 Authenticator untuk auto-generate OTP (Opsional)", default="")
    parser.add_argument("--save", action="store_true", help="Simpan kredensial ke config_account.json")
    parser.add_argument("--force", action="store_true", help="Paksa login ulang meskipun cookie masih ada")
    args = parser.parse_args()

    c, x = get_valid_cookie(
        cli_user=args.username,
        cli_pass=args.password,
        cli_otp_secret=args.otp_secret,
        cli_otp=args.otp,
        force_login=args.force,
        save_account=args.save
    )

    if c:
        print("\n✨ Sesi berhasil diperbarui dan siap digunakan!")
    else:
        sys.exit(1)
