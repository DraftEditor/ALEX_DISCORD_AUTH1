import subprocess

proc = subprocess.run("python BOT.py & python Flask.py",
                      shell=True,
                      stdout=subprocess.PIPE)
outs, errs = proc.communicate()
print(outs.decode("ascii"))
