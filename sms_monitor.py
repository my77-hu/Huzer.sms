#!/usr/bin/env python3

import csv
import os
import re
import subprocess
import sys
from datetime import datetime


def run(command, timeout=30):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "انتهت مهلة الاتصال"
    except FileNotFoundError:
        return 127, "", "لم يتم العثور على adb"


def parse_row(line):
    """
    تحليل سطر Android content query.
    """
    values = {}

    # يدعم body الذي قد يحتوي على فاصلات في أغلب الحالات
    pattern = r"(address|body|date|read|type)=(.*?)(?=, \w+=|$)"
    matches = re.findall(pattern, line)

    for key, value in matches:
        values[key] = value.strip()

    return values


def readable_date(value):
    try:
        timestamp = int(value) / 1000
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return value or ""


def check_connection(device):
    code, stdout, stderr = run(["adb", "-s", device, "get-state"])

    if code != 0 or "device" not in stdout:
        print("[-] الهاتف غير متصل عبر ADB.")
        print(stderr.strip() or stdout.strip())
        print()
        print("نفّذ أولًا:")
        print(f"adb connect {device}")
        print("adb devices")
        sys.exit(1)


def read_sms(device):
    command = [
        "adb",
        "-s",
        device,
        "shell",
        "content",
        "query",
        "--uri",
        "content://sms/inbox",
        "--projection",
        "address:body:date:read:type",
        "--sort",
        "date DESC",
    ]

    code, stdout, stderr = run(command)

    if code != 0:
        print("[-] فشل الوصول إلى صندوق الرسائل:")
        print(stderr.strip() or stdout.strip())
        sys.exit(1)

    messages = []

    for line in stdout.splitlines():
        if "Row:" not in line and "address=" not in line:
            continue

        message = parse_row(line)

        if message:
            message["date_readable"] = readable_date(
                message.get("date", "")
            )
            messages.append(message)

    return messages


def save_text(messages, filename="sms.txt"):
    with open(filename, "w", encoding="utf-8") as file:
        for number, message in enumerate(messages, 1):
            file.write(f"الرسالة رقم {number}\n")
            file.write(f"المرسل: {message.get('address', '')}\n")
            file.write(f"التاريخ: {message.get('date_readable', '')}\n")
            file.write(f"مقروءة: {message.get('read', '')}\n")
            file.write(f"النص: {message.get('body', '')}\n")
            file.write("-" * 60)
            file.write("\n")


def save_csv(messages, filename="sms.csv"):
    with open(filename, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)

        writer.writerow([
            "المرسل",
            "النص",
            "التاريخ",
            "مقروءة",
            "النوع",
        ])

        for message in messages:
            writer.writerow([
                message.get("address", ""),
                message.get("body", ""),
                message.get("date_readable", ""),
                message.get("read", ""),
                message.get("type", ""),
            ])


def main():
    # يمكن تمرير العنوان كوسيط:
    # python read_sms.py 10.179.39.245:43397
    #
    # أو وضعه في متغير بيئة:
    # export ADB_DEVICE=10.179.39.245:43397
    device = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get("ADB_DEVICE")
    )

    if not device:
        print("طريقة الاستخدام:")
        print("python read_sms.py IP:PORT")
        print()
        print("مثال:")
        print("python read_sms.py 10.179.39.245:43397")
        sys.exit(1)

    print(f"[*] التحقق من الاتصال: {device}")
    check_connection(device)

    print("[*] قراءة الرسائل الموجودة حاليًا...")
    print("[*] لا توجد مراقبة مستمرة للرسائل الجديدة.")

    messages = read_sms(device)

    if not messages:
        print("[!] لم يتم العثور على رسائل في صندوق الوارد.")
        print("[!] قد يكون الوصول محميًا بواسطة إصدار Android أو تطبيق الرسائل.")
        return

    save_text(messages)
    save_csv(messages)

    print(f"[+] عدد الرسائل: {len(messages)}")
    print("[+] تم الحفظ في الملف: sms.txt")
    print("[+] تم الحفظ بصيغة CSV في الملف: sms.csv")
    print()

    for number, message in enumerate(messages, 1):
        print(f"--- الرسالة {number} ---")
        print(f"المرسل: {message.get('address', '')}")
        print(f"التاريخ: {message.get('date_readable', '')}")
        print(f"النص: {message.get('body', '')}")
        print()


if __name__ == "__main__":
    main()
