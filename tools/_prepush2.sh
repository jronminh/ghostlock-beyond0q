#!/bin/bash
R=/mnt/e/Library/Desktop/ghostlock-beyond0q
cd "$R"
echo "== is recovered/ tracked? =="
git ls-files recovered | head
echo "(count) $(git ls-files recovered | wc -l)"
git check-ignore -v recovered 2>&1 | head
echo "== ls recovered =="
ls -la recovered 2>&1 | head
echo "== README head =="
ls -la README* 2>&1
head -30 README.md 2>&1
echo "== .gitattributes? =="
ls -la .gitattributes 2>&1
echo "== any obvious secrets? =="
git ls-files | grep -iE "\.env|id_rsa|\.pem|\.p12|token|credential|\.keystore|google-services" | head
echo "== dumps total tracked size =="
git ls-files dumps | wc -l
git ls-files -z dumps | xargs -0 du -k 2>/dev/null | awk '{s+=$1} END{print s" KB"}'
echo "== docs list =="
ls docs 2>&1
