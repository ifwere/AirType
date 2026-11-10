import socket
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from flask import Flask, request, render_template_string
import pyautogui
import pyperclip
import platform
import time
import logging
import qrcode
from PIL import Image, ImageTk
import os
import sys
import secrets
import string
from werkzeug.serving import make_server

# --- 强制刷新终端输出 ---
try:
    sys.stdout.reconfigure(line_buffering=True)
except:
    pass

# --- Flask 应用配置 ---
app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# [修改] 1. 注释掉全局变量定义
# 全局变量存储当前的鉴权 Token
# CURRENT_TOKEN = ""


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>无线键盘</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            padding: 15px; 
            text-align: center; 
            background-color: #f5f5f7; 
            color: #333;
            box-sizing: border-box;
            height: 100%;
        }
        h2 { margin-bottom: 15px; font-weight: 600; font-size: 1.3rem; }
        .input-group { margin-bottom: 10px; }
        
        textarea {
            width: 100%; 
            height: 200px; 
            padding: 15px; 
            font-size: 16px; 
            border-radius: 12px;
            border: 1px solid #d1d1d6; 
            outline: none; 
            background: #fff;
            resize: none; 
            font-family: inherit;
            box-sizing: border-box;
            -webkit-appearance: none;
            display: block;
        }
        textarea:focus { border-color: #007AFF; }
        
        /* 新增开关样式 */
        .settings-bar {
            display: flex;
            justify-content: flex-end;
            align-items: center;
            margin-bottom: 15px;
            font-size: 14px;
            color: #666;
        }
        .settings-bar label {
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            user-select: none;
        }
        .settings-bar input[type="checkbox"] {
            width: 18px;
            height: 18px;
            accent-color: #007AFF;
        }

        .button-group { display: flex; gap: 10px; margin-bottom: 10px; }
        button {
            flex: 1; padding: 12px; font-size: 16px; color: white;
            border: none; border-radius: 12px; cursor: pointer; font-weight: 600;
            -webkit-tap-highlight-color: transparent;
        }
        button#sendBtn { background-color: #007AFF; }
        button#sendBtn:active { background-color: #0056b3; transform: scale(0.98); }
        button#clearBtn { background-color: #8e8e93; }
        button#clearBtn:active { background-color: #636366; transform: scale(0.98); }
        
        #status { 
            margin-top: 5px; 
            height: 20px; 
            line-height: 20px;
            font-size: 13px; 
            color: #34c759; 
            transition: color 0.3s;
        }
        
        .history-container { margin-top: 15px; text-align: left; }
        .history-header { display: flex; justify-content: space-between; color: #888; margin-bottom: 8px; font-size: 13px; }
        .clear-btn { color: #ff3b30; cursor: pointer; padding: 0 10px; }
        .history-list { list-style: none; padding: 0; margin: 0; padding-bottom: 40px; }
        .history-item {
            background: #fff; padding: 10px 12px; margin-bottom: 6px; border-radius: 8px; border: 1px solid #e5e5ea;
            display: flex; justify-content: space-between; cursor: pointer;
            -webkit-tap-highlight-color: transparent;
            font-size: 14px;
        }
        .history-item:active { background-color: #f0f0f0; }
        .history-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 85%; }
    </style>
</head>
<body>
    <h2>电脑远程输入板</h2>
    
    <div class="input-group">
        <textarea id="textInput" placeholder="输入文字..." autofocus autocomplete="off"></textarea>
    </div>
    
    <!-- 修改显示文本：输入完成后自动发送 -->
    <div class="settings-bar">
        <label>
            <input type="checkbox" id="autoSendSwitch" checked>
            输入完成后自动发送
        </label>
    </div>

    <div class="button-group">
        <button id="clearBtn" onclick="handleClear()">清空</button>
        <button id="sendBtn" onclick="handleSend()">发送</button>
    </div>
    <div id="status"></div>
    <div class="history-container">
        <div class="history-header"><span>最近10条记录(点击重发)</span><span class="clear-btn" onclick="clearHistory()">清空</span></div>
        <ul id="historyList" class="history-list"></ul>
    </div>
    <script>
        const input = document.getElementById('textInput');
        const status = document.getElementById('status');
        const historyList = document.getElementById('historyList');
        const autoSendSwitch = document.getElementById('autoSendSwitch');
        const MAX_HISTORY = 10;
        
        let autoSendTimer = null;
        let isComposing = false; // 标记是否正在进行输入法合成(语音/拼音)
        let ignoreNextInput = false; // 用于防止语音结束触发后触发 input被代码以为你在普通打字的冲突的锁


        window.onload = function() { renderHistory(); }
        
        // --- [新增] 监听合成事件 (关键逻辑) ---
        
        // 1. 开始语音输入或拼音输入：标记为正在合成，清除倒计时，绝对不发送
        input.addEventListener('compositionstart', function() {
            isComposing = true;
            if (autoSendTimer) clearTimeout(autoSendTimer);
            status.innerText = "正在识别/校正...";
            status.style.color = "#007AFF";
        });

        // 2. 语音输入结束/校正完成：标记结束，立即触发发送逻辑
        input.addEventListener('compositionend', function(e) {
            isComposing = false;

            // [关键] 锁住普通的 input 事件，防止它重置我们的快速发送
            ignoreNextInput = true;

            // 此时 e.data 已经是校正后的最终结果
            // 给一个小缓冲(100ms)，让人眼确认一下，或者直接发也可以
            triggerAutoSend(100); 

            // 300ms 后解开锁，恢复正常打字监听
            setTimeout(() => { ignoreNextInput = false; }, 300);
        });

        // --- 原有的 input 监听进行修改 ---
        input.addEventListener("input", function() {
            // 如果正在语音，或者刚语音完(锁住了)，则忽略此事件
            if (isComposing || ignoreNextInput) return;

            // 普通手动打字时的防抖时间 (比如 1500ms)
            triggerAutoSend(1500); 
        });

        // 封装自动发送触发器
        function triggerAutoSend(delay) {
            if (autoSendTimer) clearTimeout(autoSendTimer);
            
            if (autoSendSwitch.checked && input.value.trim().length > 0) {
                status.innerText = "准备发送...";
                status.style.color = "#888";
                
                autoSendTimer = setTimeout(() => {
                    handleSend();
                }, delay);
            } else {
                status.innerText = "";
            }
        }

        // 监听回车键
        input.addEventListener("keypress", function(e) { 
            if (e.key === "Enter") { 
                e.preventDefault(); 
                handleSend(); 
            } 
        });

        autoSendSwitch.addEventListener("change", function() {
            if (!this.checked && autoSendTimer) {
                clearTimeout(autoSendTimer);
                status.innerText = "";
            }
        });
        
        document.body.addEventListener('click', function(e) {
            if (!e.target.closest('button') && !e.target.closest('.history-item') && !e.target.closest('.clear-btn') && !e.target.closest('input[type="checkbox"]') && !e.target.closest('label') && e.target !== input) {
                if (window.getSelection().toString().length === 0) {
                    input.focus();
                }
            }
        });

        function handleSend() {
            if (autoSendTimer) clearTimeout(autoSendTimer);

            const text = input.value.trim();
            if (!text) return; // 空内容不发送
            
            saveToHistory(text);
            status.innerText = "发送中...";
            status.style.color = "#34c759";

            fetch('/type', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            }).then(r => r.json()).then(d => {
                if (d.success) { 
                    status.innerText = "✓ 已发送"; 
                    status.style.color = "#34c759";
                    input.value = ''; 
                    setTimeout(() => {
                        if(!input.value) status.innerText = "";
                    }, 1500); 
                }
                else { 
                    status.innerText = d.message || "✕ 发送失败"; 
                    status.style.color = "#ff3b30"; 
                }
            }).catch(e => { status.innerText = "✕ 发送失败"; status.style.color = "#ff3b30"; });
        }

        function handleClear() { 
            if (autoSendTimer) clearTimeout(autoSendTimer);
            input.value = ''; 
            status.innerText = "";
            input.focus(); 
        }
        
        function getHistory() { return JSON.parse(localStorage.getItem('typeHistory') || '[]'); }
        function saveToHistory(text) {
            let h = getHistory().filter(i => i !== text);
            h.unshift(text);
            localStorage.setItem('typeHistory', JSON.stringify(h.slice(0, MAX_HISTORY)));
            renderHistory();
        }
        function renderHistory() {
            historyList.innerHTML = '';
            getHistory().forEach(t => {
                const li = document.createElement('li');
                li.className = 'history-item';
                li.onclick = () => { input.value = t; handleSend(); };
                li.innerHTML = `<span class="history-text">${t.replace(/&/g,'&amp;').replace(/</g,'&lt;')}</span><span>⤶</span>`;
                historyList.appendChild(li);
            });
        }
        function clearHistory() { localStorage.removeItem('typeHistory'); renderHistory(); }
    </script>
</body>
</html>
"""


IS_MAC = platform.system() == 'Darwin'
PASTE_KEY = 'command' if IS_MAC else 'ctrl'

# --- 资源路径处理 ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Flask Server 线程封装 ---
class ServerThread(threading.Thread):
    def __init__(self, app, host, port):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.server = None
        self.app = app
        self.error = None
        self.daemon = True # 设置为守护线程

    def run(self):
        try:
            self.server = make_server(self.host, self.port, self.app)
            self.server.serve_forever()
        except Exception as e:
            self.error = e
            print(f"Server Error: {e}")

    def shutdown(self):
        if self.server:
            self.server.shutdown()

@app.route('/')
def index(): 
    return render_template_string(HTML_TEMPLATE)

@app.route('/type', methods=['POST'])
def type_text():
    # [修改] 4. 注释掉 Token 相关的全局变量引用
    # global CURRENT_TOKEN
    data = request.get_json()
    
    # [修改] 5. 注释掉后端鉴权检查逻辑
    # token = data.get('token', '')
    # if not token or token != CURRENT_TOKEN:
    #     return {'success': False, 'message': '验证失败，请重新扫码'}, 403

    try:
        text = data.get('text', '')
        if text:
            pyperclip.copy(text)
            time.sleep(0.3) 
            pyautogui.keyDown(PASTE_KEY)
            time.sleep(0.1)
            pyautogui.press('v')
            time.sleep(0.1)
            pyautogui.keyUp(PASTE_KEY)
            return {'success': True}
    except Exception as e: 
        print(f"Type Error: {e}")
        return {'success': False, 'message': '服务器内部错误'}
    return {'success': False}

def get_best_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

def get_all_ips():
    ips = set()
    try:
        hostname = socket.gethostname()
        addrs = socket.getaddrinfo(hostname, None)
        for addr in addrs:
            ip = addr[4][0]
            if ':' in ip: continue 
            if ip.startswith('169.254.'): continue 
            ips.add(ip)
    except: pass
    
    best = get_best_lan_ip()
    if best and best != '127.0.0.1':
        ips.add(best)
    
    ip_list = list(ips)
    if len(ip_list) > 1 and '127.0.0.1' in ip_list:
        ip_list.remove('127.0.0.1')

    def ip_sort_key(x):
        if x == best: return 0  
        if x.startswith('192.168.'): return 1
        return 99 

    ip_list.sort(key=ip_sort_key)
    return ip_list

def find_free_port(start_port=9000):
    port = start_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except OSError: port += 1
    return start_port

# def generate_token():
#     """生成 2 位 Token (小写字母 + 数字)"""
#     chars = string.ascii_lowercase + string.digits
#     return ''.join(secrets.choice(chars) for _ in range(2))

class ServerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AirType")
        
        #self.root.geometry("300x450")
        self.root.resizable(False, False)
        self.root.protocol('WM_DELETE_WINDOW', self.quit_app)

        self.best_ip = get_best_lan_ip()
        self.all_ips = get_all_ips()
        
        default_ip = self.all_ips[0] if self.all_ips else '127.0.0.1'
        self.ip_var = tk.StringVar(value=default_ip)
        
        port = find_free_port(9000)
        self.port_var = tk.StringVar(value=str(port))
        
        self.server_thread = None
        self.is_running = False
        # self.tray_icon = None
        
        # try:
        #     import pystray
        #     from pystray import MenuItem as item
        #     self.has_pystray = True
        # except ImportError:
        #     self.has_pystray = False
        
        self.setup_ui()
        self.setup_icon()
        #self.create_tray_icon()
        
        self.on_ip_changed()
        
        # 延迟自动启动
        self.root.after(100, self.toggle_server)

        # --- [关键点 2] macOS Dock 栏点击事件 ---
        # 当你在 Dock 栏点击应用图标时，触发 show_window 把窗口找回来
        if platform.system() == 'Darwin':
            try:
                self.root.createcommand('::tk::mac::ReopenApplication', self.show_window)
            except AttributeError:
                pass

        # --- [关键点 3] 15秒后自动隐藏窗口 ---
        # 这里的 15000 是毫秒，即 15 秒
        self.auto_hide_timer = self.root.after(15000, self.hide_window)

    def setup_ui(self):
        main_frame = tk.Frame(self.root, padx=15, pady=20)
        main_frame.pack(expand=True, fill='both')

        label_title = tk.Label(main_frame, text="手机扫描此二维码连接:", font=("Arial", 11, "bold"))
        label_title.pack(anchor='w')
        
        self.ip_combo = ttk.Combobox(main_frame, textvariable=self.ip_var,
                                     values=self.all_ips, font=("Arial", 10), state='readonly')
        self.ip_combo.pack(fill='x', pady=(5, 10))
        self.ip_combo.bind('<<ComboboxSelected>>', self.on_ip_changed)

        tk.Label(main_frame, text="端口:", font=("Arial", 10)).pack(anchor='w')
        self.port_entry = tk.Entry(main_frame, textvariable=self.port_var, font=("Arial", 10))
        self.port_entry.pack(fill='x', pady=(0, 15))

        self.btn_start = tk.Button(main_frame, text="启动服务", command=self.toggle_server,
                                   bg="#007AFF", fg="white", font=("Arial", 12, "bold"),
                                   relief="flat", pady=8, cursor="hand2")
        self.btn_start.pack(fill='x', pady=(0, 10))

        # if not IS_MAC and self.has_pystray:
        #     self.btn_minimize = tk.Button(main_frame, text="最小化到托盘", command=self.hide_window,
        #                                   bg="#f0f0f0", fg="#333", relief="flat", pady=5)
        #     self.btn_minimize.pack(fill='x')

        self.qr_frame = tk.Frame(main_frame, bg="white", bd=1, relief="solid")
        self.qr_frame.pack(pady=20)
        self.qr_label = tk.Label(self.qr_frame, bg="white")
        self.qr_label.pack(padx=10, pady=10)

        # 链接标签
        self.url_label = tk.Label(main_frame, text="", fg="blue", font=("Arial", 9, "underline"), cursor="hand2")
        self.url_label.pack(fill='x')
        self.url_label.bind("<Button-1>", self.open_browser)

        self.tip_label = tk.Label(main_frame, text="请确保手机和电脑在同一 Wi-Fi 下", fg="#888", font=("Arial", 8))
        self.tip_label.pack(pady=(5, 0))

    def setup_icon(self):
        try:
            png_path = resource_path('icon.png')
            ico_path = resource_path('icon.ico')
            if os.path.exists(png_path):
                img = tk.PhotoImage(file=png_path)
                self.root.iconphoto(True, img)
            elif platform.system() == 'Windows' and os.path.exists(ico_path):
                self.root.iconbitmap(ico_path)
        except Exception as e: 
            print(f"Icon load error: {e}")

    def toggle_server(self):
        # [修改] 6. 注释掉 Token 生成时的全局引用
        # global CURRENT_TOKEN
        
        if self.is_running:
            # 如果正在运行，点击按钮直接退出
            self.quit_app()
            return

        try: 
            port = int(self.port_var.get())
        except ValueError: 
            messagebox.showerror("错误", "端口必须是数字")
            return

        # [修改] 7. 注释掉生成 Token 的逻辑
        # CURRENT_TOKEN = generate_token()

        self.server_thread = ServerThread(app, '0.0.0.0', port)
        self.server_thread.start()
        
        time.sleep(0.5)
        if not self.server_thread.is_alive() and self.server_thread.error:
            messagebox.showerror("启动失败", f"无法启动服务，端口 {port} 可能被占用。\n错误信息: {self.server_thread.error}")
            return

        self.is_running = True
        self.btn_start.config(text="停止服务并退出", bg="#ff3b30")
        self.port_entry.config(state='disabled')
        
        self.on_ip_changed()

    def on_ip_changed(self, event=None):
        if not self.is_running:
            return
            
        selected_ip = self.ip_var.get()
        try: port = self.port_var.get()
        except: port = "9000"

        # [修改] 8. 移除 URL 中的 Token 参数
        # url = f"http://{selected_ip}:{port}/?token={CURRENT_TOKEN}"
        url = f"http://{selected_ip}:{port}/"
        
        self.current_url = url
        self.url_label.config(text=url)

        try:
            qr = qrcode.QRCode(box_size=5, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = ImageTk.PhotoImage(qr.make_image(fill_color="black", back_color="white"))
            self.qr_label.config(image=img, text="")
            self.qr_label.image = img
        except:
            self.qr_label.config(text="二维码生成失败", image="")

        if selected_ip == '127.0.0.1':
            self.tip_label.config(text="127.0.0.1 手机无法访问，请切换 IP", fg="red")
        else:
            self.tip_label.config(text="手机扫码即可连接 (需同一 Wi-Fi)", fg="#888")

    # def create_tray_icon(self):
    #     if platform.system() == 'Darwin' or not self.has_pystray:
    #         return

    #     try:
    #         import pystray
    #         from pystray import MenuItem as item
            
    #         icon_path = resource_path('icon.png')
    #         if os.path.exists(icon_path):
    #             img = Image.open(icon_path)
    #         else:
    #             img = Image.new('RGB', (64, 64), '#007AFF')
                
    #         menu = pystray.Menu(item('显示', self.show_window), item('退出', self.quit_app))
    #         self.tray_icon = pystray.Icon("QAA", img, "AirType", menu)
    #         threading.Thread(target=self.tray_icon.run, daemon=True).start()
    #     except Exception: pass

    def hide_window(self):
        """完全隐藏窗口，但在 Dock 栏保留运行状态"""
        self.root.withdraw()

    def show_window(self, *args):
        """重新显示窗口并置顶"""
        self.root.deiconify()
        self.root.lift()  # 把窗口拉到最上层，防止被其他窗口挡住
    
    def quit_app(self, _=None, __=None):
        # 1. 立即销毁界面，让用户感觉反应迅速
        try:
            self.root.destroy()
        except Exception:
            pass

        # 2. 尝试停止托盘图标
        # if self.tray_icon: 
        #     try:
        #         self.tray_icon.stop()
        #     except Exception: pass
        
        # 3. 强制终止进程 (核弹级退出)，不等待线程清理，彻底解决卡死问题
        os._exit(0)

    def open_browser(self, e):
        import webbrowser
        webbrowser.open(self.current_url)

if __name__ == '__main__':
    root = tk.Tk()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    width, height = 300, 500
    root.geometry(f"{width}x{height}+{(sw-width)//2}+{(sh-height)//2}")
    app_gui = ServerApp(root)
    root.mainloop()