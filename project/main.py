import tkinter as tk
import psutil
from time import sleep
import os
import zipfile
import socket
from plyer import notification
from json import loads
import sys
import uuid
from threading import Thread

BANNED_MODS = ['wurst', 'meteor-client', 'liquidbounce', 'aristois', 'sigma', 'impact','phobos']
SERVER_HOST = 'mc.csec.top'  # Changed to localhost for testing, change to your server IP
SERVER_PORT = 7878
CHECK_INTERVAL = 10  # seconds
VERSION = "1.0"

def update():
    pass

def show_anti_cheat_alert(detected_mods):
    """显示反作弊警告界面"""
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.configure(bg='black')
    root.bind('<Escape>', lambda e: root.quit())

    main_frame = tk.Frame(root, bg='black')
    main_frame.pack(expand=True, fill='both')

    alert_text = f"""CSEC MC ANTI-CHEAT

检测到的作弊MOD:
{', '.join(detected_mods)}

按ESC退出"""

    # 添加logo
    try:
        logo_image = tk.PhotoImage(file='logo.png')
        logo_label = tk.Label(main_frame, image=logo_image, bg='black')
        logo_label.image = logo_image
        logo_label.pack(pady=20)
    except Exception as e:
        print(f"无法加载logo.png: {e}")

    display = tk.Label(
        main_frame,
        text=alert_text,
        font=('Arial', 48, 'bold'),
        fg='white',
        bg='black',
        justify='center'
    )
    display.pack(expand=True)

    root.mainloop()


def get_minecraft_processes():
    """获取所有Minecraft Java进程"""
    minecraft_processes = []
    
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if (process.info['name'] and 
                ('java' in process.info['name'].lower() or 
                 'javaw' in process.info['name'].lower())):
                
                cmdline = process.info['cmdline']
                if cmdline and any('minecraft' in str(arg).lower() for arg in cmdline):
                    minecraft_processes.append(process.info)
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
            
    return minecraft_processes


def get_mods(gamedir):
    """获取游戏目录下的mod文件"""
    mods_dir = os.path.join(gamedir, 'mods')
    if os.path.exists(mods_dir):
        return [f for f in os.listdir(mods_dir) if f.endswith('.jar')]
    return []


def read_mod_info(mod_path):
    """从mod的jar文件中读取fabric.mod.json信息"""
    try:
        with zipfile.ZipFile(mod_path, 'r') as zip_file:
            # 尝试读取Fabric mod信息
            if 'fabric.mod.json' in zip_file.namelist():
                with zip_file.open('fabric.mod.json') as file:
                    content = file.read().decode('utf-8')
                    mod_data = loads(content)
                    return mod_data.get('id', None)
            # 尝试读取Forge mod信息
            elif 'mcmod.info' in zip_file.namelist():
                with zip_file.open('mcmod.info') as file:
                    content = file.read().decode('utf-8')
                    mod_data = loads(content)
                    if isinstance(mod_data, list) and len(mod_data) > 0:
                        return mod_data[0].get('modid', None)
            # 尝试读取META-INF/mods.toml (Forge 1.13+)
            elif 'META-INF/mods.toml' in zip_file.namelist():
                # 简单解析TOML格式
                with zip_file.open('META-INF/mods.toml') as file:
                    content = file.read().decode('utf-8')
                    for line in content.split('\n'):
                        if line.strip().startswith('modId'):
                            return line.split('=')[1].strip().strip('"\'')
    except Exception as e:
        print(f"读取mod信息失败 {mod_path}: {e}")
    return None


def connect_to_server():
    """连接到服务器，带重试机制"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((SERVER_HOST, SERVER_PORT))
            print(f"✓ 成功连接到服务器 {SERVER_HOST}:{SERVER_PORT}")
            return s
        except Exception as e:
            print(f"✗ 连接失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                sleep(retry_delay)
    
    return None


def send_message(sock, message):
    """发送消息到服务器 (带换行符)"""
    try:
        sock.send(f"{message}\n".encode('utf-8'))
        print(f"→ 发送: {message}")
        return True
    except Exception as e:
        print(f"✗ 发送消息失败: {e}")
        return False


def receive_message(sock):
    """从服务器接收消息"""
    try:
        sock.settimeout(5)  # Set timeout for receiving
        data = sock.recv(1024).decode('utf-8').strip()
        if data:
            print(f"← 接收: {data}")
        return data
    except socket.timeout:
        return None
    except Exception as e:
        print(f"✗ 接收消息失败: {e}")
        return None


def main():
    """主函数"""
    print("=" * 50)
    print("CSEC MC Anti-Cheat Client v5.0")
    print("=" * 50)
    
    sock = connect_to_server()
    if not sock:
        print("✗ 无法连接到服务器，退出程序")
        sys.exit(1)
    
    authenticated = False
    last_username = None
    client_uuid = str(uuid.uuid4())
    
    try:
        while True:
            procs = get_minecraft_processes()
            
            if len(procs) > 0:
                print(f"\n✓ 检测到 {len(procs)} 个Minecraft进程")
                
                # 提取游戏目录和用户名
                gamedirs = []
                username = None
                
                for proc in procs:
                    cmd = proc['cmdline']
                    for i in range(len(cmd)):
                        if cmd[i] == '--gameDir' and i + 1 < len(cmd):
                            gamedirs.append(cmd[i + 1])
                        if cmd[i] == '--username' and i + 1 < len(cmd):
                            username = cmd[i + 1]
                
                print(f"用户名: {username}")
                print(f"游戏目录: {gamedirs}")
                
                if username and not authenticated:
                    auth_message = f"AUTH:{username}:{client_uuid}"
                    if not send_message(sock, auth_message):
                        print("✗ 连接丢失，尝试重连...")
                        sock = connect_to_server()
                        if not sock:
                            break
                        continue
                    
                    # Wait for OK response
                    response = receive_message(sock)
                    if response == "OK":
                        authenticated = True
                        last_username = username
                        print(f"✓ 认证成功: {username}")
                    else:
                        print(f"✗ 认证失败: {response}")
                        sleep(2)
                        continue
                
                if not authenticated:
                    sleep(1)
                    continue
                
                # 收集所有mod
                all_mod_names = set()
                detected_banned_mods = []
                
                for gamedir in gamedirs:
                    mods = get_mods(gamedir)
                    print(f"→ 在 {gamedir} 中找到 {len(mods)} 个mod文件")
                    
                    for mod_file in mods:
                        mod_path = os.path.join(gamedir, 'mods', mod_file)
                        mod_id = read_mod_info(mod_path)
                        
                        if mod_id:
                            all_mod_names.add(mod_id)
                            
                            # 检查是否为禁用mod
                            if any(banned in mod_id.lower() for banned in BANNED_MODS):
                                detected_banned_mods.append(mod_id)
                                print(f"⚠️  检测到禁用mod: {mod_id}")
                
                if all_mod_names:
                    mod_list_str = str(sorted(list(all_mod_names)))
                    mod_message = f"MODS:{mod_list_str}"
                    
                    if not send_message(sock, mod_message):
                        print("✗ 发送mod列表失败，重置连接")
                        authenticated = False
                        sock = connect_to_server()
                        if not sock:
                            break
                        continue
                    
                    response = receive_message(sock)
                    send_message(sock,"DETECT")
                    ingame = receive_message(sock) == "INGAME"
                    if response and response.startswith("CHEATER:") and ingame:
                        # Server detected cheats
                        banned_mods = response.split(":", 1)[1].split(",")
                        print(f"⚠️  服务器检测到作弊mod: {banned_mods}")
                        alert = Thread(target=show_anti_cheat_alert, args=(banned_mods,))
                        alert.start()
                        # After showing alert, continue monitoring
                    elif response == "OK":
                        print("✓ Mod列表已接受")
                    else:
                        print("未加入服务器")
                    
                else:
                    print("→ 未检测到mod")
            else:
                print("\n→ 未检测到Minecraft进程，等待...")
                if authenticated:
                    authenticated = False
                    last_username = None
            
            sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n✓ 程序被用户中断")
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if sock:
            try:
                sock.close()
            except:
                pass
        print("✓ 客户端已关闭")


if __name__ == '__main__':
    main()
