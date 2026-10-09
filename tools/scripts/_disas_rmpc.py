import subprocess
out=subprocess.run(["aarch64-linux-gnu-objdump","-D","-b","binary","-m","aarch64","-EL",
                    "--adjust-vma=0xffffff80080b2eec","/tmp/rmpc.bin"],
                   capture_output=True,text=True).stdout.splitlines()
lo=0xffffff80080b3080; hi=0xffffff80080b3140
for l in out:
    try: a=int(l.split(":")[0].strip(),16)
    except: continue
    if lo<=a<=hi: print(l)
