import paramiko
import os, tempfile

script = """
import torch
print("torch ok")
print("CUDA available:", torch.cuda.is_available())
print("CUDA version:", torch.version.cuda)
print("Device count:", torch.cuda.device_count())
if torch.cuda.is_available():
    print("Device name:", torch.cuda.get_device_name(0))
    x = torch.randn(3,3).cuda()
    print("CUDA tensor ok:", x)
else:
    print("No CUDA device")
"""

# Write script locally
local = os.path.join(tempfile.gettempdir(), "check_cuda.py")
with open(local, "w") as f:
    f.write(script)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('8.141.107.59', username='root', password='SE_2026mon41', timeout=10)

sftp = client.open_sftp()
sftp.put(local, "/tmp/check_cuda.py")
sftp.close()

stdin, stdout, stderr = client.exec_command("python3 /tmp/check_cuda.py 2>&1")
print(stdout.read().decode())
err = stderr.read().decode().strip()
if err:
    lines = [l for l in err.split("\n") if 'UserWarning' not in l and 'warning' not in l.lower()]
    if lines:
        print("STDERR:", "\n".join(lines)[:500])

# Also check CUDA_PATH and nvcc
stdin2, stdout2, stderr2 = client.exec_command("which nvcc 2>/dev/null; nvcc --version 2>/dev/null; echo ---; ls /usr/local/cuda*/bin/nvcc 2>/dev/null; echo ---; ldconfig -p | grep cudart 2>/dev/null | head -3")
print("\n=== nvcc ===")
print(stdout2.read().decode()[:500])

client.close()
os.remove(local)
