#!/usr/bin/env python3
import base64, string

tok = ("IxJCDiMnLjMuLAg/ARceDA07FAg7Nh4lFzssIDs2ByAzMUEgOzEUQDMQMCMBOyw/"
       "HichEQ0kQSwjAB8ODxcGBR4xOUADMSwNHjgHKRcRPjEDCx4vEgAfDjQIFAshGyAz"
       "OyUpGzw2ITUDCywkOyQgHiMbLx8XER4LOzYeJi8bAhQDBzM4ITYsBDJABkIeCzwG"
       "HgM8FCMkNDEjCxVACTghHzInDQYuFx8rIwAvJCFAMxE8EQY5NRshDjURPho0ES8k"
       "NRYhOR44LwsJEQc5NBsjKyEAPg4hAAYsLjgeLDQRHg4yJTMsMiUNKzwAPh8mGzk5"
       "FyUzDTUHQQEuByADISxBIwMnOUANQAokMzYCICMXPjkDFzA1CS8pDTsxHhwzQAZC"
       "DS8gJjMkNkAjBy4XAwc7FBIvKQcjLz4bAQM0OS8wISMvAyxBFwg7BjgxMDMNCxU5"
       "IyQ8MB4kPDk4MEEHLwsiOThALyQhOEEmMic+QDhAHgo1OCAmAy8vIy8ILCYNMS8S"
       "Lwc+HyE4Myk4MT4DIwMFKy4nBz8JETA2HhIUPTU4IEImJwcbLyUuKTQXHiASCywJ"
       "DRcsFiMlCiQhOzQ/JzsUOgMIPkEhCAceMjsuBiM4BkIjAzQUIwM7FCMDCD8jORMT")

STD = string.ascii_uppercase + string.ascii_lowercase + string.digits + "+/"
b64std = STD + "="

def b64dec(s):
    s2 = s + "=" * ((4 - len(s) % 4) % 4)
    return base64.b64decode(s2, validate=False)

def score(b):
    if not b:
        return 0
    return sum(1 for x in b if 32 <= x < 127 or x in (9, 10, 13)) / len(b)

print("== standard b64 ==")
d0 = b64dec(tok)
print("len", len(d0), "printable", round(score(d0), 2), d0[:48].hex())

print("== alphabet-rotation brute force ==")
best = []
for shift in range(64):
    tab = {ch: STD[(i - shift) % 64] for i, ch in enumerate(STD)}
    mapped = "".join(tab.get(c, c) for c in tok)
    try:
        d = b64dec(mapped)
    except Exception:
        continue
    if d:
        best.append((score(d), shift, d[:80]))
best.sort(reverse=True)
for s, sh, head in best[:6]:
    print("shift %2d  printable %.2f  %r" % (sh, s, head[:70]))

print("== single-byte XOR on standard decode ==")
hits = []
for k in range(256):
    x = bytes(b ^ k for b in d0)
    if score(x) > 0.9:
        hits.append((score(x), k, x[:80]))
hits.sort(reverse=True)
for s, k, head in hits[:6]:
    print("xor 0x%02x  printable %.2f  %r" % (k, s, head[:70]))
if not hits:
    print("  (no single-byte xor key yields >90% printable)")
