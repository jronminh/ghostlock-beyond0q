#!/bin/bash
cd ~/ghostlock/src || exit 1
echo "=== README_Kernel.txt (G9700) ==="
unzip -p SM-G9700_12_Opensource.zip README_Kernel.txt
echo
echo "=== extract G9700 Kernel.tar.gz ==="
mkdir -p g9700 && cd g9700
unzip -o ../SM-G9700_12_Opensource.zip Kernel.tar.gz >/dev/null
tar -xzf Kernel.tar.gz
echo "--- top-level ---"
ls -la | head -40
cd ..
echo
echo "=== G970W kernel.txt ==="
unzip -p SM-G970W_12_Opensource_*.zip G970WVLS8IWD1_kernel.txt
echo
echo "=== extract G970W overlay ==="
mkdir -p g970w && cd g970w
unzip -o ../SM-G970W_12_Opensource_*.zip 'G970WVLS8IWD1_kernel.tar.gz' >/dev/null
tar -xzf G970WVLS8IWD1_kernel.tar.gz
echo "--- G970W overlay tree ---"
find . -maxdepth 3 | head -60
