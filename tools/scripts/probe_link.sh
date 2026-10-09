#!/bin/bash
command -v curl >/dev/null 2>&1 || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl >/dev/null 2>&1

URL='https://s05.ooo/v2/IxJCDiMnLjMuLAg/ARceDA07FAg7Nh4lFzssIDs2ByAzMUEgOzEUQDMQMCMBOyw/HichEQ0kQSwjAB8ODxcGBR4xOUADMSwNHjgHKRcRPjEDCx4vEgAfDjQIFAshGyAzOyUpGzw2ITUDCywkOyQgHiMbLx8XER4LOzYeJi8bAhQDBzM4ITYsBDJABkIeCzwGHgM8FCMkNDEjCxVACTghHzInDQYuFx8rIwAvJCFAMxE8EQY5NRshDjURPho0ES8kNRYhOR44LwsJEQc5NBsjKyEAPg4hAAYsLjgeLDQRHg4yJTMsMiUNKzwAPh8mGzk5FyUzDTUHQQEuByADISxBIwMnOUANQAokMzYCICMXPjkDFzA1CS8pDTsxHhwzQAZCDS8gJjMkNkAjBy4XAwc7FBIvKQcjLz4bAQM0OS8wISMvAyxBFwg7BjgxMDMNCxU5IyQ8MB4kPDk4MEEHLwsiOThALyQhOEEmMic+QDhAHgo1OCAmAy8vIy8ILCYNMS8SLwc+HyE4Myk4MT4DIwMFKy4nBz8JETA2HhIUPTU4IEImJwcbLyUuKTQXHiASCywJDRcsFiMlCiQhOzQ/JzsUOgMIPkEhCAceMjsuBiM4BkIjAzQUIwM7FCMDCD8jORMT'

echo "###### curl HEAD (follow redirects) ######"
curl -sS -I -L --max-time 25 -A 'Mozilla/5.0' "$URL" 2>&1 | head -50
echo

echo "###### decode token (first stage) ######"
TOKEN="${URL##*/v2/}"
echo "$TOKEN" | base64 -d 2>/dev/null | xxd | head -24
echo

echo "###### token decoded (ascii) ######"
echo "$TOKEN" | base64 -d 2>/dev/null | strings -n 3 | head -20
