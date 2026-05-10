#!/usr/bin/env python3
import paramiko
import base64

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("8.141.107.59", username="root", password="SE_2026mon41")

def run(cmd):
    print(f"> {cmd[:100]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out[:500])
    if err:
        print("ERR:", err[:500])
    print()

# 1. Create dirs
run("mkdir -p /opt/buaa-se-aid/AIDetector/code/backend/backend-code/media/organization_logos")
run("mkdir -p /opt/buaa-se-aid/AIDetector/code/backend/backend-code/media/avatars")

# 2. Create 1x1 white PNG via base64
png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
cmd = f"echo '{png_b64}' | base64 -d > /opt/buaa-se-aid/AIDetector/code/backend/backend-code/media/avatars/default.png"
run(cmd)

# 3. Create 1x1 grey JPEG via base64
jpeg_b64 = "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYI4Q/JhM2RGYlUmKf/aAAwDAQACEQMRAD8A0NSoLw/sANfJ/wD/2Q=="
cmd = f"echo '{jpeg_b64}' | base64 -d > /opt/buaa-se-aid/AIDetector/code/backend/backend-code/media/organization_logos/bloom.jpg"
run(cmd)

# 4. Permissions
run("chmod 644 /opt/buaa-se-aid/AIDetector/code/backend/backend-code/media/organization_logos/bloom.jpg /opt/buaa-se-aid/AIDetector/code/backend/backend-code/media/avatars/default.png")
run("chown -R www-data:www-data /opt/buaa-se-aid/AIDetector/code/backend/backend-code/media/organization_logos /opt/buaa-se-aid/AIDetector/code/backend/backend-code/media/avatars")

# 5. Verify files
run("ls -la /opt/buaa-se-aid/AIDetector/code/backend/backend-code/media/organization_logos/")
run("ls -la /opt/buaa-se-aid/AIDetector/code/backend/backend-code/media/avatars/")

# 6. Optimize get_task_summary - check current function
run("sed -n '845,902p' /opt/buaa-se-aid/AIDetector/code/backend/backend-code/core/views/views_admin.py")

# 7. Test the API now
run("curl -s -o /dev/null -w '%{http_code}' http://8.141.107.59/media/organization_logos/bloom.jpg")
run("curl -s -o /dev/null -w '%{http_code}' http://8.141.107.59/media/avatars/default.png")

print("\n=== DONE ===")
ssh.close()
