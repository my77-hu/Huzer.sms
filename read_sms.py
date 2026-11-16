#!/usr/bin/env python3

import re
import subprocess
import sys
import time
from datetime import datetime


CHECK_EVERY_SECONDS = 5


def run(command, timeout=20):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "انتهت مهلة الأمر"
    except FileNotFoundError:
        return 127, "", "adb غير مثبت"


def find_devices():
    code, stdout, stderr = run(["adb", "devices"])

    if code != 0:
        print("[-] تعذر تشغيل adb:")
        print(stderr.strip())
        sys.exit(1)

    devices = []

    for line in stdout.splitlines():
        line = line.strip()

        if not line or line.startswith("List of devices"):
            continue

        parts = line.split()

        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])

    return devices


def choose_device():
    devices = find_devices()

    if not devices:
        print("[-] لم يتم العثور على جهاز متصل.")
        print()
        print("نفّذ أولًا:")
        print("adb devices")
        print()
        print("ثم تأكد من ظهور الجهاز بحالة device.")
        sys.exit(1)

    if len(devices) == 1:
        return devices[0]

    print("تم العثور على أكثر من جهاز:")
    for index, device in enumerate(devices, 1):
        print(f"{index}. {device}")

    while True:
        try:
            choice = int(input("اختر رقم الجهاز: "))
            if 1 <= choice <= len(devices):
                return devices[choice - 1]
        except ValueError:
            pass

        print("اختيار غير صحيح.")


def parse_sms_line(line):
    """
    يحلل سطر content query ويستخرج رقم الرسالة والمرسل والنص والتاريخ.
    """

    result = {}

    # يلتقط القيم حتى بداية الحقل التالي
    pattern = r"(_id|address|body|date|read|type)=(.*?)(?=, \w+=|$)"

    for key, value in re.findall(pattern, line):
        result[key] = value.strip()

    return result


def format_date(value):
    try:
        timestamp = int(value) / 1000
        return datetime.fromtimestamp(timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    except Exception:
        return value or ""


def read_inbox(device):
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
        "_id:address:body:date:read:type",
        "--sort",
        "date ASC",
    ]

    code, stdout, stderr = run(command, timeout=30)

    if code != 0:
        print("[-] فشل قراءة صندوق الرسائل:")
        print(stderr.strip() or stdout.strip())
        return []

    messages = []

    for line in stdout.splitlines():
        if "Row:" not in line and "_id=" not in line:
            continue

        message = parse_sms_line(line)

        if message.get("_id"):
            message["date_readable"] = format_date(
                message.get("date", "")
            )
            messages.append(message)

    return messages


def message_key(message):
    """
    نستخدم _id لمنع عرض الرسالة نفسها أكثر من مرة.
    """
    return message.get("_id") or (
        message.get("address", ""),
        message.get("body", ""),
        message.get("date", "")
    )


def print_message(message, title="رسالة"):
    print()
    print("=" * 60)
    print(title)
    print(f"المعرّف: {message.get('_id', '')}")
    print(f"المرسل: {message.get('address', '')}")
    print(f"التاريخ: {message.get('date_readable', '')}")
    print(f"مقروءة: {message.get('read', '')}")
    print(f"النص: {message.get('body', '')}")
    print("=" * 60)


def main():
    print("[*] البحث عن جهاز ADB متصل تلقائيًا...")
    device = choose_device()

    print(f"[+] الجهاز المستخدم: {device}")
    print("[*] قراءة الرسائل الموجودة حاليًا...")

    known_ids = set()
    current_messages = read_inbox(device)

    for message in current_messages:
        known_ids.add(message_key(message))
        print_message(message, "رسالة موجودة حاليًا")

    print()
    print(
        f"[+] تم تحميل {len(current_messages)} رسالة موجودة."
    )
    print(
        f"[*] المراقبة فعالة؛ سيتم الفحص كل {CHECK_EVERY_SECONDS} ثوانٍ."
    )
    print("[*] اضغط CTRL+C للإيقاف.")

    try:
        while True:
            devices = find_devices()

            if device not in devices:
                print("[-] انقطع اتصال الجهاز، سيتم البحث عنه مجددًا...")
                time.sleep(CHECK_EVERY_SECONDS)
                continue

            messages = read_inbox(device)

            for message in messages:
                key = message_key(message)

                if key not in known_ids:
                    known_ids.add(key)
                    print_message(message, "رسالة جديدة")

            time.sleep(CHECK_EVERY_SECONDS)

    except KeyboardInterrupt:
        print()
        print("[+] تم إيقاف المراقبة.")


if __name__ == "__main__":
    main()
