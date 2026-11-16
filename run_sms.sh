#!/data/data/com.termux/files/usr/bin/bash

set -u

PAIRING_SERVICE="adb-tls-pairing"
DEBUG_SERVICE="adb-tls-connect"
DISCOVERY_WAIT=3

echo "[*] تشغيل خادم ADB..."
adb start-server >/dev/null 2>&1

find_service() {
    local service="$1"

    adb mdns services 2>/dev/null | awk -v wanted="$service" '
        $0 ~ wanted {
            for (i = 1; i <= NF; i++) {
                if ($i ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+$/) {
                    print $i
                    exit
                }
            }
        }
    '
}

echo "[*] البحث عن منفذ الاقتران تلقائيًا..."
sleep "$DISCOVERY_WAIT"

PAIR_ENDPOINT="$(find_service "$PAIRING_SERVICE")"

if [ -z "$PAIR_ENDPOINT" ]; then
    echo "[-] لم يتم العثور تلقائيًا على منفذ الاقتران."
    echo
    echo "تأكد من:"
    echo "1. تفعيل التصحيح اللاسلكي."
    echo "2. فتح شاشة الاقتران باستخدام رمز الاقتران."
    echo "3. اتصال الهاتف وTermux بنفس شبكة Wi-Fi."
    echo
    echo "إذا لم يدعم جهازك mDNS، فسيكون إدخال عنوان الاقتران يدويًا ضروريًا."
    exit 1
fi

echo "[+] تم العثور على عنوان الاقتران: $PAIR_ENDPOINT"
echo

read -r -s -p "أدخل رمز الاقتران الظاهر على الهاتف: " PAIR_CODE
echo

if [ -z "$PAIR_CODE" ]; then
    echo "[-] لم يتم إدخال رمز."
    exit 1
fi

echo "[*] تنفيذ الاقتران..."
PAIR_RESULT="$(adb pair "$PAIR_ENDPOINT" "$PAIR_CODE" 2>&1)"
echo "$PAIR_RESULT"

if ! echo "$PAIR_RESULT" | grep -qi "success\|successfully"; then
    echo "[-] فشل الاقتران."
    exit 1
fi

echo "[+] تم الاقتران بنجاح."
echo "[*] البحث عن منفذ التصحيح تلقائيًا..."
sleep "$DISCOVERY_WAIT"

DEBUG_ENDPOINT="$(find_service "$DEBUG_SERVICE")"

if [ -z "$DEBUG_ENDPOINT" ]; then
    echo "[-] لم يتم العثور تلقائيًا على منفذ التصحيح."
    echo "اترك شاشة التصحيح اللاسلكي مفتوحة وحاول مرة أخرى."
    exit 1
fi

echo "[+] تم العثور على منفذ التصحيح: $DEBUG_ENDPOINT"

CONNECT_RESULT="$(adb connect "$DEBUG_ENDPOINT" 2>&1)"
echo "$CONNECT_RESULT"

if ! echo "$CONNECT_RESULT" | grep -qi "connected\|already connected"; then
    echo "[-] فشل الاتصال بالهاتف."
    exit 1
fi

echo "[+] تم الاتصال بالهاتف."
echo
adb devices

echo
echo "[*] تشغيل برنامج قراءة الرسائل..."
echo "[*] اضغط CTRL+C لإيقاف المراقبة."
echo

python read_sms.py
