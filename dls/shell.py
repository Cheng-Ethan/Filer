import html
import json
import os
import pty
import re
import select
import signal
import subprocess
import threading
import time

from .templates import _ICON_HELP
from .textenc import _decode_console

_ANSI_RE = re.compile(
    r'\x1B(?:\[[0-9;?]*[ -/]*[@-~]'
    r'|\][^\x07]*(?:\x07|\x1B\\)'
    r'|[()*+][ -/0-9A-Za-z]'
    r'|(?![\[\]()*+])[\x30-\x7E])')

# 正在运行的任务：task_id -> {'proc': Popen, 'cancelled': bool}
_RUNNING_CMDS = {}
_RUNNING_LOCK = threading.Lock()


def _signal_group(proc, sig):
    try:
        os.killpg(os.getpgid(proc.pid), sig)
    except Exception:
        try:
            proc.send_signal(sig)
        except Exception:
            pass


def _escalate_kill(proc):
    """先发 SIGINT（等同 Ctrl+C），1.5 秒仍未退出则 SIGKILL 整个进程组。"""
    deadline = time.time() + 1.5
    while time.time() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.1)
    _signal_group(proc, signal.SIGKILL)


class ShellMixin:
    def _shell_html(self, fs_cwd):
        sh_dir = json.dumps(fs_cwd, ensure_ascii=False)
        return (
            '<div class="shell" id="shell">'
            '<div class="shhead">'
            '<button class="shtog" id="shtog" title="折叠/展开输出" >▾</button>'
            '<span class="shlabel">📂 当前目录：</span>'
            '<span class="shcwd">' + html.escape(fs_cwd) + '</span>'
            '<button class="shhist" id="shhist" type="button" title="命令历史搜索（Ctrl+S）">🕘</button>'
            '<button class="shhist" id="shkeybtn" type="button" title="快捷操作（停止 / 清屏 / 上一条 / 下一条）">⌨</button>'
            '<button class="shhelp" id="shhelp" type="button" title="使用说明">' + _ICON_HELP + '</button>'
            '</div>'
            '<div class="shhint" id="shhint" hidden>💡 输入命令后按回车执行；Ctrl+C 停止/清空，Ctrl+S 搜索历史，Ctrl+L 清屏，↑/↓ 切换历史；手机端可点右上角 🕘 打开历史、⌨ 打开快捷操作；输出区域可用滚轮/双指滑动上下查看，PageUp/PageDown 翻页。</div>'
            '<div class="shhistpanel" id="shhistpanel" hidden>'
            '<div class="shsearchrow">'
            '<input id="shsearch" type="text" autocomplete="off" spellcheck="false" '
            'placeholder="搜索命令历史…（Esc 关闭）">'
            '</div>'
            '<div class="shlists">'
            '<div class="shlist"><div class="shlisttitle">🔥 常用 Top 10</div>'
            '<div class="shchips" id="shfreq"></div></div>'
            '<div class="shlist"><div class="shlisttitle">🕘 最近使用</div>'
            '<div class="shchips" id="shrecent"></div></div>'
            '</div>'
            '</div>'
            '<pre class="shout collapsed" id="shout"></pre>'
            '<button class="shback" id="shback" type="button" hidden>↓ 回到底部</button>'
            '<div class="shkeys" id="shkeypanel" hidden>'
            '<button class="shkey" id="shcancel" type="button" title="运行中：终止命令；空闲：清空输入（Ctrl+C）">■ 停止<small>Ctrl+C</small></button>'
            '<button class="shkey" id="shkeyhist" type="button" title="搜索命令历史（Ctrl+S）">🕘 历史<small>Ctrl+S</small></button>'
            '<button class="shkey" id="shkeyclear" type="button" title="清空屏幕输出（Ctrl+L）">🧹 清屏<small>Ctrl+L</small></button>'
            '<button class="shkey" id="shkeyprev" type="button" title="上一条历史命令（↑）">↑ 上一条</button>'
            '<button class="shkey" id="shkeynext" type="button" title="下一条历史命令（↓）">↓ 下一条</button>'
            '</div>'
            '<div class="shinput"><span class="shprompt">$</span>'
            '<input id="shinput" type="text" autocomplete="off" spellcheck="false" '
            'placeholder="例如：ls -la · du -sh * · find . -name xxx · cd docs">'
            '<span class="shstatus" id="shstatus"></span>'
            '</div>'
            '</div>'
            '<script>'
            'var SH_DIR=' + sh_dir + ';'
            'var shell=document.getElementById("shell");'
            'var shtog=document.getElementById("shtog");'
            'var shout=document.getElementById("shout");'
            'shtog.onclick=function(){'
            'var c=shout.classList.toggle("collapsed");'
            'if(c)SH_SAVED_TOP=shout.scrollTop;else shout.scrollTop=SH_SAVED_TOP;'
            'shtog.textContent=c?"▸":"▾";shUpdateBack();};'
            'var shhelp=document.getElementById("shhelp");'
            'var shhint=document.getElementById("shhint");'
            'shhelp.onclick=function(){shhint.hidden=!shhint.hidden;};'
            'var shin=document.getElementById("shinput");'
            'var shcancel=document.getElementById("shcancel");'
            'var shstatus=document.getElementById("shstatus");'
            'var shhistBtn=document.getElementById("shhist");'
            'var shhistPanel=document.getElementById("shhistpanel");'
            'var shkeybtn=document.getElementById("shkeybtn");'
            'var shkeypanel=document.getElementById("shkeypanel");'
            'var shsearch=document.getElementById("shsearch");'
            'var shfreq=document.getElementById("shfreq");'
            'var shrecent=document.getElementById("shrecent");'
            'var shback=document.getElementById("shback");'
            'var shkeyhist=document.getElementById("shkeyhist");'
            'var shkeyclear=document.getElementById("shkeyclear");'
            'var shkeyprev=document.getElementById("shkeyprev");'
            'var shkeynext=document.getElementById("shkeynext");'
            'var SHBUSY=false,SHTASK=null,SHCTL=null,SHHIST_IDX=-1;'
            'var SHAUTO=true,SH_SAVED_TOP=0;'
            'var SH_RECENT="dls_cmd_recent",SH_COUNT="dls_cmd_count";'
            'var SHHIST={recent:[],count:{}};'
            'function shLoad(){'
            'try{SHHIST.recent=JSON.parse(localStorage.getItem(SH_RECENT)||"[]")||[];}catch(e){SHHIST.recent=[];}'
            'try{SHHIST.count=JSON.parse(localStorage.getItem(SH_COUNT)||"{}")||{};}catch(e){SHHIST.count={};}'
            'if(!(SHHIST.recent instanceof Array))SHHIST.recent=[];'
            'if(!SHHIST.count||typeof SHHIST.count!=="object")SHHIST.count={};}'
            'function shSave(){'
            'try{localStorage.setItem(SH_RECENT,JSON.stringify(SHHIST.recent.slice(0,100)));'
            'localStorage.setItem(SH_COUNT,JSON.stringify(SHHIST.count));}catch(e){}}'
            'function shRecord(cmd){'
            'SHHIST.count[cmd]=(SHHIST.count[cmd]||0)+1;'
            'var i=SHHIST.recent.indexOf(cmd);if(i>=0)SHHIST.recent.splice(i,1);'
            'SHHIST.recent.unshift(cmd);'
            'if(SHHIST.recent.length>100)SHHIST.recent.length=100;'
            'shSave();shRender();}'
            'function shTop(){'
            'var arr=Object.keys(SHHIST.count).map(function(k){return [k,SHHIST.count[k]];});'
            'arr.sort(function(a,b){return b[1]-a[1]||SHHIST.recent.indexOf(a[0])-SHHIST.recent.indexOf(b[0]);});'
            'return arr.slice(0,10).map(function(x){return x[0];});}'
            'function shPick(cmd){shin.value=cmd;shin.focus();'
            'try{shin.setSelectionRange(cmd.length,cmd.length);}catch(e){}}'
            'function shChips(host,items){'
            'host.innerHTML="";'
            'if(!items.length){var e=document.createElement("span");e.className="shempty";'
            'e.textContent="暂无记录";host.appendChild(e);return;}'
            'for(var i=0;i<items.length;i++){(function(cmd){'
            'var b=document.createElement("button");b.type="button";b.className="shchip";'
            'b.textContent=cmd;b.title=cmd;'
            'b.onclick=function(){shPick(cmd);};host.appendChild(b);})(items[i]);}}'
            'function shRender(){'
            'var q=(shsearch.value||"").trim().toLowerCase();'
            'function flt(a){return !q||a.toLowerCase().indexOf(q)>=0;}'
            'shChips(shfreq,shTop().filter(flt));'
            'shChips(shrecent,SHHIST.recent.slice(0,10).filter(flt));}'
            'function shToggleHist(force){'
            'var show=(force===undefined)?shhistPanel.hidden:!!force;'
            'shhistPanel.hidden=!show;'
            'if(show){shkeypanel.hidden=true;shsearch.value="";shRender();shsearch.focus();}}'
            'function shToggleKeys(force){'
            'var show=(force===undefined)?shkeypanel.hidden:!!force;'
            'shkeypanel.hidden=!show;'
            'if(show)shhistPanel.hidden=true;}'
            'shhistBtn.onclick=function(){shToggleHist();};'
            'shkeybtn.onclick=function(){shToggleKeys();};'
            'shsearch.addEventListener("input",shRender);'
            'shsearch.addEventListener("keydown",function(e){'
            'if(e.key==="Escape"){e.preventDefault();shToggleHist(false);shin.focus();return;}'
            'if(e.key==="Enter"){e.preventDefault();var first=shhistPanel.querySelector(".shchip");'
            'if(first){shPick(first.textContent);shToggleHist(false);}return;}'
            'if(e.ctrlKey&&(e.key==="s"||e.key==="S")){e.preventDefault();shToggleHist(false);shin.focus();}});'
            'function shHistNav(dir){'
            'if(!SHHIST.recent.length)return;'
            'if(dir<0){'
            'if(SHHIST_IDX<SHHIST.recent.length-1){SHHIST_IDX++;shin.value=SHHIST.recent[SHHIST_IDX];}}'
            'else if(SHHIST_IDX>0){SHHIST_IDX--;shin.value=SHHIST.recent[SHHIST_IDX];}'
            'else if(SHHIST_IDX===0){SHHIST_IDX=-1;shin.value="";}'
            'try{var n=shin.value.length;shin.setSelectionRange(n,n);}catch(e){}}'
            'function shSetBusy(b){SHBUSY=b;shcancel.classList.toggle("active",b);'
            'shkeybtn.classList.toggle("running",b);'
            'shstatus.textContent=b?"运行中…":"";}'
            'function shClear(){if(SHBUSY)return;shout.textContent="";'
            'SHAUTO=true;SH_SAVED_TOP=0;shUpdateBack();}'
            'function shNearBottom(){return shout.scrollHeight-shout.scrollTop-shout.clientHeight<40;}'
            'function shUpdateBack(){shback.hidden=SHAUTO||shout.classList.contains("collapsed")'
            '||shout.scrollHeight<=shout.clientHeight+1;}'
            'function shWrite(txt){var st=shout.scrollTop;shout.textContent=txt;'
            'if(SHAUTO)shout.scrollTop=shout.scrollHeight;else shout.scrollTop=st;'
            'shUpdateBack();}'
            'shout.addEventListener("scroll",function(){'
            'SHAUTO=shNearBottom();shUpdateBack();});'
            'shback.onclick=function(){SHAUTO=true;shout.scrollTop=shout.scrollHeight;'
            'shUpdateBack();};'
            'shell.addEventListener("wheel",function(e){'
            'if(!e.deltaY||shout.classList.contains("collapsed"))return;'
            'if(shout.contains(e.target)||shhistPanel.contains(e.target))return;'
            'if(shout.scrollHeight<=shout.clientHeight+1)return;'
            'var atTop=shout.scrollTop<=0;'
            'var atBottom=shout.scrollTop+shout.clientHeight>=shout.scrollHeight-1;'
            'if((e.deltaY<0&&atTop)||(e.deltaY>0&&atBottom))return;'
            'shout.scrollTop+=e.deltaY;e.preventDefault();},{passive:false});'
            'function shCancel(){'
            'if(!SHBUSY)return;'
            'shstatus.textContent="正在停止…";'
            'if(SHTASK){try{fetch("/cmd/cancel",{method:"POST",'
            'headers:{"Content-Type":"application/json"},'
            'body:JSON.stringify({id:SHTASK})}).catch(function(){});}catch(e){}}'
            'var ctl=SHCTL;'
            'setTimeout(function(){if(SHBUSY&&SHCTL===ctl){try{ctl.abort();}catch(e){}}},3000);}'
            'function shRun(v){'
            'shSetBusy(true);'
            'SHTASK="t"+Date.now().toString(36)+Math.random().toString(36).slice(2,8);'
            'var tid=SHTASK;'
            'shout.classList.remove("collapsed");shtog.textContent="▾";'
            'SHAUTO=true;shWrite("$ "+v+"\\n…");'
            'try{SHCTL=new AbortController();}catch(e){SHCTL=null;}'
            'fetch("/cmd",{method:"POST",headers:{"Content-Type":"application/json"},'
            'body:JSON.stringify({cmd:v,dir:SH_DIR,stream:true,id:tid}),'
            'signal:SHCTL?SHCTL.signal:undefined}).then(function(r){'
            'if(!r.ok)throw new Error("HTTP "+r.status);'
            'var ct=r.headers.get("Content-Type")||"";'
            'if(ct.indexOf("json")>=0||!r.body){'
            'return r.json().then(function(d){if(d.nav){location.href=d.nav;return;}'
            'SHAUTO=true;shWrite(d.out||"(无输出)");});}'
            'var reader=r.body.getReader(),dec=new TextDecoder(),buf="";'
            'function pump(){return reader.read().then(function(x){'
            'if(x.done)return;'
            'buf+=dec.decode(x.value,{stream:true});'
            'shWrite(buf);'
            'return pump();});}'
            'return pump().then(function(){buf+=dec.decode();shWrite(buf);});'
            '}).catch(function(e){'
            'if(e&&e.name==="AbortError")return;'
            'shWrite((shout.textContent||"")+"\\n请求失败："+e);'
            '}).then(function(){'
            'if(SHTASK===tid){SHTASK=null;SHCTL=null;shSetBusy(false);}});}'
            'shcancel.onclick=function(){'
            'if(SHBUSY){shCancel();return;}'
            'if(shin.value){shin.value="";SHHIST_IDX=-1;}shin.focus();};'
            'shkeyhist.onclick=function(){shToggleHist();};'
            'shkeyclear.onclick=shClear;'
            'shkeyprev.onclick=function(){shHistNav(-1);shin.focus();};'
            'shkeynext.onclick=function(){shHistNav(1);shin.focus();};'
            'shin.addEventListener("input",function(){SHHIST_IDX=-1;});'
            'shin.addEventListener("keydown",function(e){'
            'if(e.ctrlKey&&!e.altKey&&!e.metaKey&&(e.key==="s"||e.key==="S")){'
            'e.preventDefault();shToggleHist();return;}'
            'if(e.ctrlKey&&!e.altKey&&!e.metaKey&&(e.key==="c"||e.key==="C")){'
            'var sel=shin.selectionStart!==shin.selectionEnd;'
            'if(SHBUSY){e.preventDefault();shCancel();return;}'
            'if(!sel){e.preventDefault();if(shin.value){shin.value="";SHHIST_IDX=-1;}}'
            'return;}'
            'if(e.ctrlKey&&!e.altKey&&!e.metaKey&&(e.key==="l"||e.key==="L")){'
            'e.preventDefault();shClear();return;}'
            'if(e.key==="Enter"){e.preventDefault();if(SHBUSY)return;'
            'var v=shin.value.trim();if(!v)return;shin.value="";SHHIST_IDX=-1;'
            'shRecord(v);shRun(v);return;}'
            'if(e.key==="PageUp"||e.key==="PageDown"){e.preventDefault();'
            'if(!shout.classList.contains("collapsed")){'
            'shout.scrollTop+=(e.key==="PageUp"?-1:1)*Math.max(80,shout.clientHeight*0.8);}'
            'return;}'
            'if(e.key==="ArrowUp"){e.preventDefault();shHistNav(-1);return;}'
            'if(e.key==="ArrowDown"){e.preventDefault();shHistNav(1);return;}});'
            'document.addEventListener("keydown",function(e){'
            'if(e.defaultPrevented)return;'
            'if(e.key==="Escape"){'
            'if(!shkeypanel.hidden){e.preventDefault();shkeypanel.hidden=true;return;}'
            'if(!shhistPanel.hidden){e.preventDefault();shhistPanel.hidden=true;return;}}'
            'if(e.ctrlKey&&!e.altKey&&!e.metaKey&&(e.key==="s"||e.key==="S")){'
            'var ae=document.activeElement;'
            'var other=ae&&(ae.tagName==="INPUT"||ae.tagName==="TEXTAREA"||ae.tagName==="SELECT")'
            '&&!shell.contains(ae);'
            'if(!other){e.preventDefault();shToggleHist();return;}}'
            'if(e.ctrlKey&&!e.altKey&&!e.metaKey&&(e.key==="l"||e.key==="L")){'
            'if(shell.contains(document.activeElement)){e.preventDefault();shClear();return;}}'
            'if(SHBUSY&&e.ctrlKey&&!e.altKey&&!e.metaKey&&(e.key==="c"||e.key==="C")){'
            'var sel=window.getSelection?window.getSelection().toString():"";'
            'if(!sel){e.preventDefault();shCancel();}}});'
            'window.addEventListener("beforeunload",function(){'
            'if(SHBUSY&&SHTASK){try{fetch("/cmd/cancel",{method:"POST",'
            'headers:{"Content-Type":"application/json"},'
            'body:JSON.stringify({id:SHTASK}),keepalive:true});}catch(e){}}});'
            'shLoad();shRender();'
            '</script>'
        )
    def _handle_cmd(self):
        length = int(self.headers.get('Content-Length', 0) or 0)
        if not length or length > 1024 * 1024:
            self.send_error(400, 'Bad request')
            return
        try:
            data = json.loads(self.rfile.read(length).decode('utf-8', 'replace'))
        except Exception:
            self.send_error(400, 'Bad json')
            return
        cmd = str(data.get('cmd', '')).strip()
        if not cmd:
            self.send_error(400, 'Empty command')
            return

        base = os.path.abspath(self.directory) if hasattr(self, 'directory') else os.getcwd()
        d = str(data.get('dir', '')).strip() or base
        if not os.path.isabs(d):
            d = os.path.join(base, d)
        d = os.path.abspath(d)
        if not (d == base or d.startswith(base + os.sep)) or not os.path.isdir(d):
            d = base

        # cd 特殊处理：切换前端浏览目录
        cm = re.match(r'^(cd|go|jump)\s+(\S+)\s*$', cmd, re.I)
        if cm:
            target = cm.group(2)
            t = os.path.join(d, target) if not os.path.isabs(target) else target
            t = os.path.abspath(t)
            if not (t == base or t.startswith(base + os.sep)):
                resp = {'code': 1, 'out': '路径不在服务目录内'}
            elif os.path.isdir(t):
                rel = t[len(base):].replace(os.sep, '/')
                resp = {'code': 0, 'out': '已切换目录：' + t,
                        'nav': '/' + rel.lstrip('/') if rel else '/'}
            else:
                resp = {'code': 1, 'out': '不是目录：' + t}
            self._send_json(resp)
            return

        task_id = str(data.get('id', '')).strip()[:64] or None

        if data.get('stream'):
            self._stream_cmd(cmd, d, task_id)
            return

        try:
            out, code = self._run_shell(cmd, d, task_id)
        except Exception as e:
            out, code = '执行失败：' + str(e), 1
        if len(out) > 200000:
            out = out[:200000] + '\n…[输出已截断]'
        self._send_json({'code': code, 'out': out})
    def _handle_cmd_cancel(self):
        length = int(self.headers.get('Content-Length', 0) or 0)
        if length <= 0 or length > 64 * 1024:
            self._send_json({'ok': False, 'error': 'bad request'}, status=400)
            return
        try:
            data = json.loads(self.rfile.read(length).decode('utf-8', 'replace'))
        except Exception:
            self._send_json({'ok': False, 'error': 'bad json'}, status=400)
            return
        task_id = str(data.get('id', '')).strip()[:64]
        ok = self._cancel_cmd(task_id) if task_id else False
        self._send_json({'ok': True, 'cancelled': ok})
    def _register_cmd(self, task_id, proc):
        if not task_id:
            return
        with _RUNNING_LOCK:
            _RUNNING_CMDS[task_id] = {'proc': proc, 'cancelled': False}
    def _finish_cmd(self, task_id):
        if not task_id:
            return
        with _RUNNING_LOCK:
            _RUNNING_CMDS.pop(task_id, None)
    def _is_cancelled(self, task_id):
        if not task_id:
            return False
        with _RUNNING_LOCK:
            ent = _RUNNING_CMDS.get(task_id)
            return bool(ent and ent.get('cancelled'))
    def _cancel_cmd(self, task_id):
        """按 task_id 中断命令：先 SIGINT（等同 Ctrl+C），必要时升级为 SIGKILL。"""
        with _RUNNING_LOCK:
            ent = _RUNNING_CMDS.get(task_id)
            if not ent:
                return False
            ent['cancelled'] = True
            proc = ent['proc']
        _signal_group(proc, signal.SIGINT)
        threading.Thread(target=_escalate_kill, args=(proc,), daemon=True).start()
        return True
    def _run_shell(self, cmd, d, task_id=None):
        """伪终端执行命令（一次性收集）：不限时长，可用 task_id 取消；剥离 ANSI。"""
        proc, master = self._spawn_shell(cmd, d)
        self._register_cmd(task_id, proc)
        buf = bytearray()
        try:
            for data, _to in self._shell_chunks(proc, master):
                if _to:
                    break
                buf.extend(data)
            if proc.poll() is not None:
                self._drain_shell(master, buf.extend)
        finally:
            cancelled = self._is_cancelled(task_id)
            self._finish_cmd(task_id)
            self._shell_cleanup(proc, master)
        text = self._fmt(bytes(buf))
        code = proc.returncode if proc.returncode is not None else 0
        if cancelled:
            text += '\n[已取消]'
            code = 130
        return text, code
    def _stream_cmd(self, cmd, d, task_id=None):
        """伪终端执行命令（实时流式输出到浏览器）：不限时长，可用 task_id 取消。"""
        proc, master = self._spawn_shell(cmd, d)
        self._register_cmd(task_id, proc)
        try:
            self._begin_stream()
        except Exception:
            self._finish_cmd(task_id)
            self._shell_cleanup(proc, master)
            return
        total = 0
        pending = b''

        def emit(raw):
            nonlocal pending, total
            data = pending + raw
            pending = b''
            cut = self._ansi_partial_tail(data)
            if cut is not None:
                data, pending = data[:cut], data[cut:]
            t = self._fmt(data).encode('utf-8')
            self._chunk(t)
            total += len(t)

        try:
            for data, _to in self._shell_chunks(proc, master):
                if _to:
                    break
                emit(data)
                if total > 800000:
                    self._chunk('\n[输出量过大，已自动截断]'.encode('utf-8'))
                    break
            if proc.poll() is not None:
                self._drain_shell(master, emit)
        except Exception:
            pass
        finally:
            cancelled = self._is_cancelled(task_id)
            self._finish_cmd(task_id)
            self._shell_cleanup(proc, master)
        if pending:
            try:
                self._chunk(self._fmt(pending).encode('utf-8'))
            except Exception:
                pass
        if cancelled:
            self._chunk('\n[已取消]'.encode('utf-8'))
        else:
            code = proc.returncode if proc.returncode is not None else 0
            self._chunk(('\n[退出码 %d]' % code).encode('utf-8'))
        try:
            self.wfile.write(b'0\r\n\r\n')
            self.wfile.flush()
        except Exception:
            pass
    def _drain_shell(self, master, sink):
        """进程已退出后，把 pty 中残留的输出读完（最多等待 0.3 秒静默）。"""
        while True:
            r, _, _ = select.select([master], [], [], 0.3)
            if not r:
                break
            try:
                chunk = os.read(master, 65536)
            except OSError:
                break
            if not chunk:
                break
            sink(chunk)
    def _spawn_shell(self, cmd, d):
        """启动 pty shell 子进程，返回 (proc, master)。三方 fds 接 pty，独立进程组。"""
        # 剔除 DL_AUTH，避免用户在终端里执行 env 看到凭据。
        env = {k: v for k, v in os.environ.items() if k != 'DL_AUTH'}
        env.setdefault('TERM', 'xterm-256color')
        env.setdefault('COLORTERM', 'truecolor')
        env.setdefault('LANG', 'C.UTF-8')
        master, slave = pty.openpty()
        proc = subprocess.Popen(cmd, shell=True, cwd=d, env=env,
                                stdin=slave, stdout=slave, stderr=slave,
                                close_fds=True, start_new_session=True)
        try:
            os.close(slave)
        except OSError:
            pass
        return proc, master
    def _shell_chunks(self, proc, master, timeout=None):
        """按需产出 (bytes, timed_out)。timeout 为 None 表示不限时长。"""
        deadline = None if timeout is None else time.time() + timeout
        while True:
            if proc.poll() is not None:
                break
            if deadline is None:
                wait = 0.5
            else:
                remaining = deadline - time.time()
                if remaining <= 0:
                    yield b'', True
                    return
                wait = min(remaining, 0.5)
            r, _, _ = select.select([master], [], [], wait)
            if not r:
                if deadline is not None and time.time() >= deadline:
                    yield b'', True
                    return
                continue
            try:
                chunk = os.read(master, 65536)
            except OSError:
                break
            if not chunk:
                break
            yield chunk, False
    def _shell_cleanup(self, proc, master):
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            proc.wait(timeout=2)
        except Exception:
            pass
        try:
            os.close(master)
        except OSError:
            pass
    def _fmt(self, raw):
        """剥离 ANSI/终端转义（CSI、OSC、SCS 如 (B、ESC=/> 等）、归一化换行。"""
        text = _ANSI_RE.sub('', _decode_console(raw))
        return text.replace('\r\n', '\n').replace('\r', '\n')
    def _ansi_partial_tail(self, data):
        """若 data 末尾存在一个被截断的转义序列，返回其起始下标（便于留到下一块），否则 None。"""
        idx = data.rfind(b'\x1b')
        if idx == -1:
            return None
        if _ANSI_RE.match(data[idx:].decode('latin-1')):
            return None
        return idx
    def _begin_stream(self):
        self.protocol_version = 'HTTP/1.1'
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close')
        self.send_header('Transfer-Encoding', 'chunked')
        self.end_headers()
    def _chunk(self, data):
        if data:
            self.wfile.write(('%x\r\n' % len(data)).encode('ascii') + data + b'\r\n')
            self.wfile.flush()

