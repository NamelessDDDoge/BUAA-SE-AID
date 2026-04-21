import subprocess
import os
import signal
import re

def find_trigger_processes():
    try:
        output = subprocess.check_output(['ps', 'aux']).decode('utf-8')
    except subprocess.CalledProcessError as e:
        print(f"执行ps aux命令失败: {e}")
        return []

    current_pid = os.getpid()  # 获取当前进程PID
    pids = []
    for line in output.splitlines()[1:]:  # 跳过标题行
        line = line.strip()
        if not line:
            continue
        
        # 更健壮的列解析方式
        parts = line.split(None, 10)
        if len(parts) < 11:
            continue
        
        pid = int(parts[1])
        cmd = parts[10]

        # 排除当前进程自身
        if pid == current_pid:
            continue

        # 加强正则表达式匹配精度
        if re.search(r'(^|/|\b)trigger\.py(\s|$)', cmd):
            pids.append(str(pid))
    
    return pids

def kill_processes(pids):
    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGTERM)
            print(f"已发送SIGTERM信号给进程 {pid}")
        except ProcessLookupError:
            print(f"进程 {pid} 不存在或已终止")
        except PermissionError:
            print(f"权限不足，无法终止进程 {pid}")
        except Exception as e:
            print(f"终止进程 {pid} 时发生错误: {e}")

def clear_trigger():
    trigger_pids = find_trigger_processes()
    if not trigger_pids:
        print("未找到运行 trigger.py 的进程")
    print(f"找到以下运行 trigger.py 的进程: {trigger_pids}")
    kill_processes(trigger_pids)