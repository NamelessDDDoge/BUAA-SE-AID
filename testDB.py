from sshtunnel import SSHTunnelForwarder
import psycopg2
import getpass

# --- 配置信息 ---
ECS_HOST = '114.55.151.162'  # 替换为您的 ECS 公网 IP
ECS_USER = 'root'  # 替换为您的 ECS 登录用户名（如 root 或 ecs-user）
ECS_PASSWORD = 'SE2026_mon41'  # 替换为您的 ECS 密码（如果使用密钥认证，见下方说明）

RDS_HOST = 'pgm-2ze340z1a21f2xb7po.pg.rds.aliyuncs.com'  # RDS 内网地址
RDS_PORT = 5432
DB_NAME = 'detect'
DB_USER = 'super_admin'
DB_PASSWORD = 'SE2026_mon41'

LOCAL_PORT = 5433  # 本地映射端口

print("正在建立 SSH 隧道...")

try:
    # 创建 SSH 隧道
    with SSHTunnelForwarder(
        (ECS_HOST, 22),
        ssh_username=ECS_USER,
        ssh_password=ECS_PASSWORD,  # 如果使用密钥，改为 ssh_private_key_file='path/to/key.pem'
        remote_bind_address=(RDS_HOST, RDS_PORT),
        local_bind_address=('127.0.0.1', LOCAL_PORT)
    ) as tunnel:
        print(f"SSH 隧道建立成功，本地端口：{tunnel.local_bind_port}")

        # 通过隧道连接数据库
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=tunnel.local_bind_port,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        cursor = conn.cursor()
        print("正在查询数据库版本...")
        cursor.execute("SELECT version();")
        result = cursor.fetchone()
        print(f"连接成功，数据库版本：{result[0]}")

        # 在这里执行您的其他业务逻辑...

        cursor.close()
        conn.close()
        print("连接已关闭，隧道自动断开。")

except Exception as e:
    print(f"发生错误：{e}")
