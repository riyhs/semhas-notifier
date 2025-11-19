import json
import logging
import os
import smtplib
import sqlite3
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

load_dotenv()

URL_TARGET = "https://silat.fatisda.uns.ac.id/"
FILE_STATE = "data/data_terakhir.json"
DB_FILE = "data/subscribers.db"
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = os.environ.get("SMTP_PORT")
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_SENDER_EMAIL = os.environ.get("SMTP_SENDER_EMAIL")
SMTP_SENDER_NAME = os.environ.get("SMTP_SENDER_NAME")
APP_BASE_URL = os.environ.get("APP_BASE_URL")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "rahasia_super_secure_random_string")

serializer = URLSafeTimedSerializer(app.secret_key)


def init_db():
    """Inisialisasi database dan folder data."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS subscribers (email TEXT PRIMARY KEY)""")
    conn.commit()
    conn.close()


def get_subscribers():
    """Ambil semua email subscriber."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT email FROM subscribers")
    emails = [row[0] for row in c.fetchall()]
    conn.close()
    return emails


def add_subscriber(email):
    """Tambah subscriber baru."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO subscribers (email) VALUES (?)", (email,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def remove_subscriber(email):
    """Hapus subscriber."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM subscribers WHERE email = ?", (email,))
    conn.commit()
    conn.close()


def load_previous_data():
    try:
        with open(FILE_STATE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_current_data(data):
    with open(FILE_STATE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_latest_schedule():
    """Scraping data dari website."""
    logger.info("Menjalankan Scraper...")
    try:
        response = requests.get(URL_TARGET, timeout=20)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Error request ke website: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    tab_pane = soup.find("div", id="2")
    if not tab_pane:
        return []
    table_body = tab_pane.find("tbody")
    if not table_body:
        return []

    latest_data = []
    for row in table_body.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 8:
            penguji_text = cells[4].get_text(separator="<br>").strip()
            entry = {
                "tanggal": cells[1].text.strip(),
                "nama": cells[2].text.strip(),
                "nim": cells[3].text.strip(),
                "penguji": penguji_text,
                "jam_mulai": cells[5].text.strip(),
                "jam_selesai": cells[6].text.strip(),
                "ruang": cells[7].text.strip(),
            }
            latest_data.append(entry)
    return latest_data


def generate_unsubscribe_link(email):
    """Membuat link unsubscribe unik."""
    token = serializer.dumps(email, salt="unsubscribe-salt")
    return f"{APP_BASE_URL}/unsubscribe/{token}"


def send_email_blast(new_entries):
    """Mengirim email transaksional"""
    subscribers = get_subscribers()
    if not subscribers:
        return

    subject = f"Update SILAT UNS: {len(new_entries)} Jadwal Baru"

    try:
        with app.app_context():
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)

                sent_count = 0
                for email_dest in subscribers:
                    try:
                        unsubscribe_link = generate_unsubscribe_link(email_dest)

                        html_content = render_template(
                            "email_template.html",
                            entries=new_entries,
                            unsubscribe_link=unsubscribe_link,
                            app_url=APP_BASE_URL,
                        )

                        msg = MIMEMultipart("alternative")
                        msg["Subject"] = subject
                        msg["From"] = formataddr((SMTP_SENDER_NAME, SMTP_SENDER_EMAIL))
                        msg["To"] = email_dest

                        msg.add_header("List-Unsubscribe", f"<{unsubscribe_link}>")
                        msg.add_header(
                            "List-Unsubscribe-Post", "List-Unsubscribe=One-Click"
                        )
                        msg.add_header("Precedence", "bulk")
                        msg.add_header(
                            "X-Auto-Response-Suppress", "OOF, DR, RN, NRN, AutoReply"
                        )

                        text_content = f"Ada {len(new_entries)} jadwal baru. Buka {URL_TARGET}. Unsubscribe: {unsubscribe_link}"
                        part1 = MIMEText(text_content, "plain", "utf-8")
                        part2 = MIMEText(html_content, "html", "utf-8")

                        msg.attach(part1)
                        msg.attach(part2)

                        server.send_message(msg)
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Gagal kirim ke {email_dest}: {e}")

            logger.info(
                f"Laporan: Email terkirim ke {sent_count}/{len(subscribers)} subscriber."
            )

    except Exception as e:
        logger.error(f"SMTP Error Utama: {e}")


def scheduled_job():
    """Fungsi Scraper yang dijalankan Scheduler."""
    with app.app_context():
        current_data = get_latest_schedule()
        if not current_data:
            return

        previous_data = load_previous_data()
        previous_ids = {
            f"{d['nim']}-{d['tanggal']}-{d['jam_mulai']}" for d in previous_data
        }

        new_entries = []
        for entry in current_data:
            entry_id = f"{entry['nim']}-{entry['tanggal']}-{entry['jam_mulai']}"
            if entry_id not in previous_ids:
                new_entries.append(entry)

        if new_entries:
            logger.info(
                f"Ditemukan {len(new_entries)} data baru. Mengirim notifikasi..."
            )
            send_email_blast(new_entries)
            save_current_data(current_data)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        email = request.form.get("email")
        if email:
            if add_subscriber(email):
                flash(
                    "Berhasil berlangganan! Cek inbox/spam untuk memastikan.", "success"
                )
            else:
                flash("Email ini sudah terdaftar.", "warning")
        return redirect(url_for("index"))
    return render_template("index.html")


@app.route("/unsubscribe/<token>")
def unsubscribe(token):
    try:
        email = serializer.loads(token, salt="unsubscribe-salt", max_age=604800)
        remove_subscriber(email)
        return render_template("unsubscribe.html", email=email, success=True)
    except SignatureExpired:
        return render_template(
            "unsubscribe.html",
            error="Link unsubscribe sudah kadaluarsa.",
            success=False,
        )
    except BadSignature:
        return render_template(
            "unsubscribe.html", error="Link unsubscribe tidak valid.", success=False
        )


init_db()

if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=scheduled_job, trigger="interval", minutes=30)
    scheduler.start()
    logger.info("Scheduler aktif (Interval: 30 menit)")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
