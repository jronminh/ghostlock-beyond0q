#!/bin/bash
cd ~/ghostlock || exit 1
mkdir -p src
CJ=src/cookies.txt
rm -f $CJ

echo "=== GET search page (with cookies) ==="
curl -s -c $CJ -A 'Mozilla/5.0' 'https://opensource.samsung.com/uploadSearch?searchValue=SM-G970W' -o src/search.html
TOKEN=$(grep -o 'name="_csrf" value="[^"]*"' src/search.html | head -1 | sed 's/.*value="//; s/"$//')
echo "csrf token: ${TOKEN:0:40}..."
echo "cookies:"; cat $CJ | grep -v '^#' | awk '{print $6"="substr($7,1,20)}'

echo
echo "=== POST /downSrcMPop uploadId=11456 ==="
curl -s -b $CJ -X POST 'https://opensource.samsung.com/downSrcMPop' \
  -A 'Mozilla/5.0' \
  -H "X-CSRF-TOKEN: $TOKEN" \
  -H 'X-Requested-With: XMLHttpRequest' \
  -H 'Referer: https://opensource.samsung.com/uploadSearch?searchValue=SM-G970W' \
  --data 'uploadId=11456' -o src/down.html
echo "--- response (first 120 lines) ---"
sed -n '1,120p' src/down.html
