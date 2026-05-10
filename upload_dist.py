import paramiko
import os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('8.141.107.59', username='root', password='SE_2026mon41')

sftp = client.open_sftp()

local_dist = r'C:\Users\admin\Desktop\SE\BUAA-SE-AID\AIDetector\code\frontend\frontend-admin\dist'
remote_dist = '/opt/buaa-se-aid/AIDetector/code/frontend/frontend-admin/dist'

stdin, stdout, stderr = client.exec_command('rm -rf ' + remote_dist)
stdout.channel.recv_exit_status()

count = 0
for root, dirs, files in os.walk(local_dist):
    for f in files:
        local_path = os.path.join(root, f)
        rel_path = os.path.relpath(local_path, local_dist)
        remote_path = remote_dist + '/' + rel_path.replace('\\', '/')
        remote_dir = os.path.dirname(remote_path)

        try:
            sftp.stat(remote_dir)
        except:
            stdin2, stdout2, stderr2 = client.exec_command('mkdir -p ' + remote_dir)
            stdout2.channel.recv_exit_status()

        sftp.put(local_path, remote_path)
        count += 1

sftp.close()
print('Uploaded %d files' % count)
client.close()
