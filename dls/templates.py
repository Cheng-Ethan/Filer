from .ui import BASE_CSS, FONT_STACK

_PREVIEW_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{i18n:preview.markdown_title}}</title>
<style>
*{box-sizing:border-box;}
body{margin:0;font-family:''' + FONT_STACK + r''';background:#f1f5f9;color:#1e293b;}
.head{position:sticky;top:0;z-index:10;}
.topbar{position:static;background:#0f172a;color:#e2e8f0;padding:10px 16px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.topbar .ttl{font-weight:600;font-size:15px;margin-right:auto;word-break:break-all;}

.tgroup{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.tlabel{font-size:13px;color:#64748b;display:inline-flex;align-items:center;gap:6px;}

.tbtn:hover{background:#eef2f7;}

.tstate{font-size:12px;color:#0f766e;}
.taudio{height:34px;max-width:340px;flex:1 1 260px;min-width:180px;}
button{font:inherit;}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:4px;height:var(--h-ctl);padding:0 var(--px-ctl);border-radius:var(--radius);font-size:var(--font-ui);border:1px solid #475569;color:#e2e8f0;background:#1e293b;text-decoration:none;cursor:pointer;box-sizing:border-box;white-space:nowrap;}
.btn:hover{background:#334155;}
@media(max-width:640px){.btn{flex:1 1 96px;}}
.box{max-width:820px;margin:24px auto;background:#fff;padding:28px 32px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,.08);line-height:1.7;}
#raw{white-space:pre-wrap;word-break:break-word;font-family:ui-monospace,Consolas,monospace;font-size:13px;color:#0f172a;background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:16px;display:none;margin:24px auto;max-width:820px;}
h1,h2,h3,h4{line-height:1.35;margin:1.2em 0 .5em;}
h1{border-bottom:2px solid #e2e8f0;padding-bottom:.3em;font-size:26px;}
h2{border-bottom:1px solid #eef2f7;padding-bottom:.25em;font-size:21px;}
h3{font-size:17px;}
a{color:#2563eb;}
code{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:4px;padding:1px 5px;font-size:.9em;font-family:ui-monospace,Consolas,monospace;}
pre{background:#0f172a;color:#e2e8f0;border-radius:8px;padding:14px;overflow-x:auto;}
pre code{background:none;border:none;padding:0;color:inherit;}
blockquote{border-left:4px solid #cbd5e1;margin:.8em 0;padding:.1em 1em;color:#475569;background:#f8fafc;}
table{border-collapse:collapse;width:100%;margin:1em 0;}
th,td{border:1px solid #e2e8f0;padding:8px 12px;text-align:left;}
th{background:#f8fafc;}
img{max-width:100%;border-radius:6px;}
hr{border:none;border-top:2px solid #e2e8f0;margin:1.5em 0;}
ul,ol{padding-left:1.6em;}
pre::-webkit-scrollbar{height:8px;}
@media(max-width:640px){.box{margin:12px;padding:18px;}#raw{margin:12px;}}
.topacts{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-left:0;}
.topacts .btn{flex:0 0 auto;min-width:var(--h-ctl);}
.topacts .btn-edit{background:#0f766e;border-color:#0f766e;color:#fff;}
.topacts .btn-edit:hover{background:#115e59;}
.topacts #tog{min-width:6.5em;}
.topbar{padding:6px 12px;gap:8px;flex-wrap:wrap;}
.topbar .ttl{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;margin-right:0;flex:1 1 auto;}
.toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:6px 12px;background:#fff;border-bottom:1px solid #e2e8f0;}
.trow{display:flex;align-items:center;gap:8px;flex-wrap:wrap;width:100%;}
#ttsGroup{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
#ttsGroup[hidden]{display:none !important;}
.tbtn{min-width:5.75em;height:var(--h-ctl);padding:0 10px;border-radius:var(--radius);border:1px solid #cbd5e1;background:#f8fafc;color:#334155;font-size:var(--font-ui);cursor:pointer;white-space:nowrap;}
.tbtn:hover{background:#eef2f7;}
.tbtn.primary{background:#0f766e;color:#fff;border-color:#0f766e;}
.tbtn.primary:hover{background:#115e59;}
.tsel{height:var(--h-ctl);border-radius:var(--radius);border:1px solid #cbd5e1;background:#fff;color:#334155;font-size:var(--font-ui);padding:0 var(--px-ctl);}
.tstate{font-size:12px;color:#0f766e;flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.tset{position:relative;flex:0 0 auto;}
.tset>summary{list-style:none;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;}
.tset>summary::-webkit-details-marker{display:none;}
.tset[open]{flex:0 0 auto;width:auto;}
@media(max-width:640px){.tset[open]{flex:1 1 100%;width:100%;max-width:none;}}
.tsetbody{position:absolute;z-index:60;left:0;top:calc(100% + 6px);display:flex;align-items:center;gap:16px;flex-wrap:wrap;width:max-content;min-width:100%;max-width:min(560px,90vw);padding:10px 12px;margin-top:0;background:#fff;border:1px solid #e2e8f0;border-radius:var(--radius);box-shadow:0 8px 24px rgba(0,0,0,.12);}
.tenc .tsetbody{left:auto;right:0;}
@media(max-width:640px){.trow{align-items:flex-start;}.tsetbody{position:static;width:100%;max-width:none;box-shadow:none;border-top:1px solid #e2e8f0;border-left:0;border-right:0;border-radius:0;padding:8px 0 2px;background:transparent;}}
.tfield{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#475569;min-width:0;}
.tfield select{max-width:150px;min-width:0;}
.tvol{width:110px;height:4px;accent-color:#0f766e;}
.taudio{position:absolute;left:-9999px;width:1px;height:1px;opacity:0;}
.enc{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:12px;}
.enc a{color:#1d4ed8;border:1px solid #cbd5e1;background:#f8fafc;text-decoration:none;padding:2px 6px;border-radius:4px;}
.enc a.on{background:#1e40af;color:#fff;border-color:#1e40af;}
@media(max-width:640px){.topbar{padding:6px 8px;}.toolbar{padding:6px 8px;gap:6px;}.tstate{flex:1 1 100%;white-space:normal;overflow:visible;}#ttsSettings .tsetbody{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;}#ttsSettings .tfield{display:flex;flex-direction:column;align-items:stretch;gap:4px;font-size:12px;min-width:0;}.tfield select{width:100%;max-width:none;min-width:0;}.tvol{width:100%;}}</style>
<script>
const MD_RAW = {{MD_TEXT}};
const MD_BASE = {{MD_BASE}};
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function escAttr(s){return s.replace(/&/g,'&amp;').replace(/"/g,'&quot;');}
function absUrl(raw){
  var u=raw.replace(/&amp;/g,'&');
  if(/^(?:[a-z][a-z0-9+.-]*:|\/|#)/i.test(u))return u;
  try{var x=new URL(u,location.origin+(MD_BASE||'/') );return x.pathname+x.search+x.hash;}catch(e){return u;}
}
function imgUrl(raw){
  var u=absUrl(raw);
  if(/^(?:data:|https?:|mailto:)/i.test(u)||u.indexOf('//')===0)return u;
  if(u.indexOf('raw=1')>=0)return u;
  return escAttr(u+(u.indexOf('?')>=0?'&':'?')+'raw=1');
}
function linkUrl(raw){
  var u=absUrl(raw);
  return escAttr(u);
}
function inline(t){
  t = esc(t);
  t = t.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g,function(m,alt,src){return '<img src="'+imgUrl(src)+'" alt="'+alt+'">';});
  t = t.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g,function(m,label,url){return '<a href="'+linkUrl(url)+'" target="_blank" rel="noopener">'+label+'</a>';});
  t = t.replace(/`([^`]*)`/g,'<code>$1</code>');
  t = t.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
  t = t.replace(/__([^_]+)__/g,'<strong>$1</strong>');
  t = t.replace(/(^|[^*])\*([^*]+)\*(?![*])/g,'$1<em>$2</em>');
  t = t.replace(/~~([^~]+)~~/g,'<del>$1</del>');
  return t;
}
function splitRow(r){var c=r.trim();if(c.charAt(0)==='|')c=c.slice(1);if(c.slice(-1)==='|')c=c.slice(0,-1);return c.split('|').map(function(x){return x.trim();});}
function renderMarkdown(src){
  var lines = src.replace(/\r\n/g,'\n').split('\n');
  var html='', para=[], i=0;
  function flushP(){if(para.length){html+='<p>'+para.map(inline).join('<br>')+'</p>';para.length=0;}}
  while(i<lines.length){
    var l=lines[i], m;
    if(l.indexOf('```')===0){var buf=[];i++;while(i<lines.length&&lines[i].indexOf('```')!==0){buf.push(esc(lines[i]));i++;}i++;flushP();html+='<pre><code>'+buf.join('\n')+'</code></pre>';continue;}
    if(m=l.match(/^(#{1,6})\s+(.*)/)){flushP();var h=m[1].length;html+='<h'+h+'>'+inline(m[2])+'</h'+h+'>';i++;continue;}
    if(/^---+$/.test(l)||/^\*{3,}$/.test(l)){flushP();html+='<hr>';i++;continue;}
    if(l.indexOf('>')===0){var q=[];while(i<lines.length&&lines[i].indexOf('>')===0){q.push(lines[i].replace(/^>\s?/,''));i++;}flushP();html+='<blockquote>'+q.map(inline).join('<br>')+'</blockquote>';continue;}
    var ordered=/^\s*\d+\.\s+/.test(l), unordered=/^\s*[*+-]\s+/.test(l)&&!/^\s*[-*+]\s*$/.test(l);
    if(ordered||unordered){var items=[];var re=ordered?/^\s*\d+\.\s+/:/^\s*[*+-]\s+/;
      while(i<lines.length){var ll=lines[i];if(ordered?/^\s*\d+\.\s+/.test(ll):/^\s*[*+-]\s+/.test(ll)){items.push(inline(ll.replace(re,'')));i++;}else break;}
      flushP();html+=(ordered?'<ol>':'<ul>')+items.map(function(x){return '<li>'+x+'</li>';}).join('')+(ordered?'</ol>':'</ul>');continue;}
    if(l.indexOf('|')>=0&&lines[i+1]&&/^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(lines[i+1])&&l.replace(/\|/g,'').trim()){
      var heads=splitRow(l);i+=2;var rows=[];
      while(i<lines.length&&lines[i].trim()){rows.push(splitRow(lines[i]));i++;}
      flushP();html+='<table><thead><tr>'+heads.map(function(x){return '<th>'+inline(x)+'</th>';}).join('')+'</tr></thead><tbody>';
      rows.forEach(function(r){html+='<tr>'+heads.map(function(_,k){return '<td>'+inline(r[k]||'')+'</td>';}).join('')+'</tr>';});
      html+='</tbody></table>';continue;}
    para.push(l);i++;
  }
  flushP();
  return html;
}
function toggleRaw(){var raw=document.getElementById('raw');var md=document.getElementById('md');var on=raw.style.display==='block';raw.style.display=on?'none':'block';md.style.display=on?'block':'none';document.getElementById('tog').textContent=on?I18N["preview.view_raw"]:I18N["preview.view_preview"];}
window.addEventListener('DOMContentLoaded',function(){document.getElementById('md').innerHTML=renderMarkdown(MD_RAW);});
</script>
</head>
<body>
<div class="head">
<div class="topbar">
  <span class="ttl" title="{{FILENAME}}">🧾 {{FILENAME}}</span>
  <div class="topacts">
    <a class="btn" href="{{BACK}}">{{i18n:common.back}}</a>
    <a class="btn" href="{{DL}}" title="{{i18n:preview.download_title}}">{{i18n:common.download}}</a>
    {{EDIT}}
    <button class="btn" id="tog" onclick="toggleRaw()">{{i18n:preview.view_raw}}</button>
  </div>{{LANGSEL}}
</div>
<div class="toolbar">
  <div class="trow">
    <div id="ttsGroup" hidden>
      <button class="tbtn primary" id="ttsBtn" type="button" title="{{i18n:preview.read_aloud}}">{{i18n:preview.read_aloud}}</button>
      <button class="tbtn" id="ttsStop" type="button">{{i18n:preview.stop}}</button>
    </div>
    <details class="tset" id="ttsSettings" hidden>
      <summary class="tbtn">{{i18n:preview.read_settings}}</summary>
      <div class="tsetbody">
        <label class="tfield">{{i18n:preview.speed}}
          <select class="tsel" id="ttsRate">
            <option value="0.75">0.75x</option>
            <option value="1" selected>1.0x</option>
            <option value="1.25">1.25x</option>
            <option value="1.5">1.5x</option>
            <option value="2">2.0x</option>
          </select>
        </label>
        <label class="tfield">{{i18n:preview.voice}}
          <select class="tsel" id="ttsVoice"></select>
        </label>
        <label class="tfield">{{i18n:preview.volume}}
          <input type="range" id="ttsVol" class="tvol" min="0" max="100" value="100">
        </label>
      </div>
    </details>
    <span class="tstate" id="ttsState"></span>
    <audio id="ttsAudio" class="taudio" preload="none"></audio>
  </div>
</div>
</div>
<div class="box" id="md"></div>
<pre class="box" id="raw"></pre>
<script>document.getElementById('raw').textContent=MD_RAW;</script>
</body>
</html>'''


_TEXT_PREVIEW_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{FILENAME}}</title>
<style>
*{box-sizing:border-box;}
body{margin:0;font-family:''' + FONT_STACK + r''';background:#f1f5f9;color:#1e293b;}
.head{position:sticky;top:0;z-index:10;}
.topbar{position:static;background:#0f172a;color:#e2e8f0;padding:10px 16px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.topbar .ttl{font-weight:600;font-size:15px;margin-right:auto;word-break:break-all;}

.tgroup{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.tlabel{font-size:13px;color:#64748b;display:inline-flex;align-items:center;gap:6px;}

.tbtn:hover{background:#eef2f7;}

.tstate{font-size:12px;color:#0f766e;}
.taudio{height:34px;max-width:340px;flex:1 1 260px;min-width:180px;}
.btn{display:inline-flex;align-items:center;justify-content:center;height:var(--h-ctl);padding:0 var(--px-ctl);border-radius:var(--radius);font-size:var(--font-ui);border:1px solid #475569;color:#e2e8f0;background:#1e293b;text-decoration:none;cursor:pointer;box-sizing:border-box;white-space:nowrap;}
.btn:hover{background:#334155;}
.note{max-width:1000px;margin:12px auto 0;padding:10px 14px;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;color:#92400e;font-size:13px;}
.wrap{max-width:1000px;margin:16px auto 40px;background:#fff;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.08);overflow:auto;}
pre{margin:0;padding:18px 20px;white-space:pre-wrap;word-break:break-word;font-family:ui-monospace,Consolas,Menlo,monospace;font-size:13px;line-height:1.6;color:#0f172a;}
.enc{display:inline-flex;gap:6px;align-items:center;font-size:12px;color:#94a3b8;flex-wrap:wrap;}
.enc a{color:#7dd3fc;text-decoration:none;padding:2px 6px;border-radius:4px;border:1px solid #334155;}
.enc a.on{background:#1e40af;color:#fff;border-color:#1e40af;}
@media(max-width:640px){.btn{flex:1 1 96px;}.wrap{margin:10px;}.tbtn,.tsel{flex:1 1 auto;}}
.topacts{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-left:0;}
.topacts .btn{flex:0 0 auto;min-width:var(--h-ctl);}
.topacts .btn-edit{background:#0f766e;border-color:#0f766e;color:#fff;}
.topacts .btn-edit:hover{background:#115e59;}
.topacts #tog{min-width:6.5em;}
.topbar{padding:6px 12px;gap:8px;flex-wrap:wrap;}
.topbar .ttl{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;margin-right:0;flex:1 1 auto;}
.toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:6px 12px;background:#fff;border-bottom:1px solid #e2e8f0;}
.trow{display:flex;align-items:center;gap:8px;flex-wrap:wrap;width:100%;}
#ttsGroup{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
#ttsGroup[hidden]{display:none !important;}
.tbtn{min-width:5.75em;height:var(--h-ctl);padding:0 10px;border-radius:var(--radius);border:1px solid #cbd5e1;background:#f8fafc;color:#334155;font-size:var(--font-ui);cursor:pointer;white-space:nowrap;}
.tbtn:hover{background:#eef2f7;}
.tbtn.primary{background:#0f766e;color:#fff;border-color:#0f766e;}
.tbtn.primary:hover{background:#115e59;}
.tsel{height:var(--h-ctl);border-radius:var(--radius);border:1px solid #cbd5e1;background:#fff;color:#334155;font-size:var(--font-ui);padding:0 var(--px-ctl);}
.tstate{font-size:12px;color:#0f766e;flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.tset{position:relative;flex:0 0 auto;}
.tset>summary{list-style:none;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;}
.tset>summary::-webkit-details-marker{display:none;}
.tset[open]{flex:0 0 auto;width:auto;}
@media(max-width:640px){.tset[open]{flex:1 1 100%;width:100%;max-width:none;}}
.tsetbody{position:absolute;z-index:60;left:0;top:calc(100% + 6px);display:flex;align-items:center;gap:16px;flex-wrap:wrap;width:max-content;min-width:100%;max-width:min(560px,90vw);padding:10px 12px;margin-top:0;background:#fff;border:1px solid #e2e8f0;border-radius:var(--radius);box-shadow:0 8px 24px rgba(0,0,0,.12);}
.tenc .tsetbody{left:auto;right:0;}
@media(max-width:640px){.trow{align-items:flex-start;}.tsetbody{position:static;width:100%;max-width:none;box-shadow:none;border-top:1px solid #e2e8f0;border-left:0;border-right:0;border-radius:0;padding:8px 0 2px;background:transparent;}}
.tfield{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#475569;min-width:0;}
.tfield select{max-width:150px;min-width:0;}
.tvol{width:110px;height:4px;accent-color:#0f766e;}
.taudio{position:absolute;left:-9999px;width:1px;height:1px;opacity:0;}
.enc{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:12px;}
.enc a{color:#1d4ed8;border:1px solid #cbd5e1;background:#f8fafc;text-decoration:none;padding:2px 6px;border-radius:4px;}
.enc a.on{background:#1e40af;color:#fff;border-color:#1e40af;}
@media(max-width:640px){.topbar{padding:6px 8px;}.toolbar{padding:6px 8px;gap:6px;}.tstate{flex:1 1 100%;white-space:normal;overflow:visible;}#ttsSettings .tsetbody{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;}#ttsSettings .tfield{display:flex;flex-direction:column;align-items:stretch;gap:4px;font-size:12px;min-width:0;}.tfield select{width:100%;max-width:none;min-width:0;}.tvol{width:100%;}}</style>
</head>
<body>
<div class="head">
<div class="topbar">
  <span class="ttl" title="{{FILENAME}}">{{FILENAME}}</span>
  <div class="topacts">
    <a class="btn" href="{{BACK}}">{{i18n:common.back}}</a>
    <a class="btn" href="{{DL}}" title="{{i18n:preview.download_title}}">{{i18n:common.download}}</a>
    {{EDIT}}
  </div>{{LANGSEL}}
</div>
<div class="toolbar">
  <div class="trow">
    <div id="ttsGroup" hidden>
      <button class="tbtn primary" id="ttsBtn" type="button" title="{{i18n:preview.read_aloud}}">{{i18n:preview.read_aloud}}</button>
      <button class="tbtn" id="ttsStop" type="button">{{i18n:preview.stop}}</button>
    </div>
    <details class="tset" id="ttsSettings" hidden>
      <summary class="tbtn">{{i18n:preview.read_settings}}</summary>
      <div class="tsetbody">
        <label class="tfield">{{i18n:preview.speed}}
          <select class="tsel" id="ttsRate">
            <option value="0.75">0.75x</option>
            <option value="1" selected>1.0x</option>
            <option value="1.25">1.25x</option>
            <option value="1.5">1.5x</option>
            <option value="2">2.0x</option>
          </select>
        </label>
        <label class="tfield">{{i18n:preview.voice}}
          <select class="tsel" id="ttsVoice"></select>
        </label>
        <label class="tfield">{{i18n:preview.volume}}
          <input type="range" id="ttsVol" class="tvol" min="0" max="100" value="100">
        </label>
      </div>
    </details>
    <details class="tset tenc">
      <summary class="tbtn">{{i18n:preview.encoding}}</summary>
      <div class="tsetbody"><span class="enc">{{ENC_LINKS}}</span></div>
    </details>
    <span class="tstate" id="ttsState"></span>
    <audio id="ttsAudio" class="taudio" preload="none"></audio>
  </div>
</div>
</div>
{{NOTE}}
<div class="wrap"><pre id="ttsSource">{{TEXT}}</pre></div>
</body>
</html>'''


_ENC_BLOCK = """    <details class="tset tenc">
      <summary class="tbtn">{{i18n:preview.encoding}}</summary>
      <div class="tsetbody"><span class="enc">{{ENC_LINKS}}</span></div>
    </details>"""


_DOC_PREVIEW_TEMPLATE = _TEXT_PREVIEW_TEMPLATE.replace(
    _ENC_BLOCK, ''
).replace(
    '<div class="wrap"><pre id="ttsSource">{{TEXT}}</pre></div>',
    '<div class="doc" id="ttsSource">{{BODY}}</div>'
).replace('</style>', '''.doc{max-width:1000px;margin:16px auto 40px;background:#fff;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.08);padding:20px 24px;line-height:1.8;}
.doc p{margin:0 0 .8em;white-space:pre-wrap;word-break:break-word;}
.doc img{max-width:100%;height:auto;display:block;margin:12px auto;border-radius:6px;}
.doc table{border-collapse:collapse;width:100%;margin:1em 0;}
.doc td,.doc th{border:1px solid #cbd5e1;padding:6px 8px;vertical-align:top;}
.doc td p{margin:0 0 .4em;}
.doc td img{margin:4px 0;}
@media(max-width:640px){.doc{margin:10px;padding:14px;}}</style>''')


_ARTICLE_TEMPLATE = _TEXT_PREVIEW_TEMPLATE.replace(
    _ENC_BLOCK, ''
).replace(
    '<div class="wrap"><pre id="ttsSource">{{TEXT}}</pre></div>',
    '<div class="article" id="ttsSource">{{BODY}}</div>'
).replace('>{{i18n:common.download}}<', '>{{i18n:preview.original}}<').replace('</style>', '''.article{max-width:900px;margin:16px auto 40px;background:#fff;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.08);padding:24px 28px;line-height:1.85;font-size:16px;}
.article .atitle{font-size:24px;line-height:1.4;margin:0 0 10px;color:#0f172a;}
.article .ameta{font-size:13px;color:#64748b;margin:0 0 20px;word-break:break-all;}
.article .acontent p{margin:0 0 .9em;word-break:break-word;}
.article .acontent img{max-width:100%;height:auto;display:block;margin:14px auto;border-radius:6px;}
.article .acontent h1,.article .acontent h2,.article .acontent h3{line-height:1.4;margin:1.2em 0 .5em;}
.article .acontent table{border-collapse:collapse;width:100%;margin:1em 0;}
.article .acontent td,.article .acontent th{border:1px solid #e2e8f0;padding:6px 8px;text-align:left;}
.article .acontent blockquote{border-left:4px solid #cbd5e1;margin:.8em 0;padding:.2em 1em;color:#475569;background:#f8fafc;}
.article .acontent pre{background:#0f172a;color:#e2e8f0;border-radius:8px;padding:14px;overflow-x:auto;white-space:pre-wrap;}
.article .acontent a{color:#1d4ed8;}
@media(max-width:640px){.article{margin:8px;padding:16px;font-size:15px;}.article .atitle{font-size:20px;}}</style>''')


_PDF_PREVIEW_TEMPLATE = _TEXT_PREVIEW_TEMPLATE.replace(
    _ENC_BLOCK, ''
).replace(
    '<div class="wrap"><pre id="ttsSource">{{TEXT}}</pre></div>',
    '<div class="pdfwrap"><iframe src="{{PDFURL}}" title="PDF"></iframe></div>'
).replace('</style>', '''.pdfwrap{max-width:1000px;margin:12px auto;height:calc(100vh - 150px);background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.08);}
.pdfwrap iframe{width:100%;height:100%;border:0;display:block;}
@media(max-width:640px){.pdfwrap{margin:6px;height:calc(100vh - 120px);}}</style>''')


_PAGES_PREVIEW_TEMPLATE = _TEXT_PREVIEW_TEMPLATE.replace(
    _ENC_BLOCK, ''
).replace(
    '<div class="wrap"><pre id="ttsSource">{{TEXT}}</pre></div>',
    '<div class="pages">{{PAGES}}</div>'
).replace('</style>', '''.pages{max-width:1000px;margin:12px auto 40px;}
.pages img{width:100%;height:auto;display:block;margin:0 auto 12px;background:#fff;border-radius:4px;box-shadow:0 2px 8px rgba(0,0,0,.12);}
@media(max-width:640px){.pages{margin:6px;}.pages img{margin-bottom:8px;}}</style>''')


_WRAP_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{FILENAME}}</title>
<style>
*{box-sizing:border-box;}
html,body{height:100%;}
body{margin:0;font-family:''' + FONT_STACK + r''';background:#0f172a;color:#e2e8f0;display:flex;flex-direction:column;}
.topbar{display:flex;align-items:center;gap:10px;padding:10px 16px;flex-wrap:wrap;background:#0f172a;}
.topbar .ttl{font-weight:600;font-size:15px;margin-right:auto;word-break:break-all;}
.btn{display:inline-flex;align-items:center;justify-content:center;height:var(--h-ctl);padding:0 var(--px-ctl);border-radius:var(--radius);font-size:var(--font-ui);border:1px solid #475569;color:#e2e8f0;background:#1e293b;text-decoration:none;white-space:nowrap;}
.btn:hover{background:#334155;}
.frame{flex:1;min-height:0;background:#fff;}
.frame iframe,.frame img,.frame video{width:100%;height:100%;border:0;display:block;object-fit:contain;background:#fff;}
.frame audio{width:100%;margin:40px auto;display:block;}
</style>
</head>
<body>
<div class="topbar">
  <span class="ttl">{{FILENAME}}</span>
  <a class="btn" href="{{BACK}}">{{i18n:preview.back_previous}}</a>
  <a class="btn" href="{{DL}}" title="{{i18n:preview.download_title}}">{{i18n:common.download}}</a>
  {{EDIT}}
</div>
<div class="frame">{{BODY}}</div>
</body>
</html>'''


_EDIT_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{FILENAME}}</title>
<style>
*{box-sizing:border-box;}
body{margin:0;font-family:''' + FONT_STACK + r''';background:#f1f5f9;color:#1e293b;}
.topbar{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:#0f172a;color:#e2e8f0;padding:8px 14px;}
.topbar .ttl{font-weight:600;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:1 1 auto;}
.topacts{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.btn{display:inline-flex;align-items:center;justify-content:center;height:var(--h-ctl);padding:0 var(--px-ctl);border-radius:var(--radius);font-size:var(--font-ui);border:1px solid #475569;color:#e2e8f0;background:#1e293b;text-decoration:none;cursor:pointer;box-sizing:border-box;white-space:nowrap;}
.btn:hover{background:#334155;}
.btn-save{background:#0f766e;border-color:#0f766e;color:#fff;}
.btn-save:hover{background:#115e59;}
.editwrap{max-width:1100px;margin:16px auto 40px;padding:0 12px;}
.editform{display:flex;flex-direction:column;gap:10px;}
.edittoolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;box-shadow:0 2px 8px rgba(0,0,0,.05);}
.editfield{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#475569;}
.editnote{font-size:12px;color:#64748b;flex:1 1 220px;min-width:0;}
.editarea{width:100%;min-height:calc(100vh - 190px);resize:vertical;border:1px solid #cbd5e1;border-radius:10px;background:#fff;color:#0f172a;padding:16px 18px;font-family:ui-monospace,Consolas,Menlo,monospace;font-size:13px;line-height:1.6;tab-size:4;box-shadow:0 2px 10px rgba(0,0,0,.06);}
.editarea:focus{outline:none;border-color:#0f766e;box-shadow:0 0 0 3px rgba(15,118,110,.12);}
.edit-error{max-width:1100px;margin:12px auto 0;padding:10px 14px;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;color:#991b1b;font-size:13px;}
@media(max-width:640px){.topbar{padding:6px 8px;}.editwrap{margin:8px auto 20px;padding:0 8px;}.editarea{min-height:calc(100vh - 230px);padding:12px;}.edittoolbar .btn{flex:1 1 auto;}}
</style>
{{EDIT_HEAD}}
</head>
<body>
<div class="topbar">
  <span class="ttl" title="{{FILENAME}}">{{FILENAME}}</span>
  <div class="topacts">
    <a class="btn" href="{{BACK}}">{{i18n:edit.back_preview}}</a>
    <a class="btn" href="{{DL}}" title="{{i18n:preview.download_title}}">{{i18n:common.download}}</a>
  </div>{{LANGSEL}}
</div>
{{NOTE}}
<div class="editwrap">{{BODY}}</div>
</body>
</html>'''


_TTS_JS = (
    '(function(){'
    'var group=document.getElementById("ttsGroup");'
    'var btn=document.getElementById("ttsBtn"),stop=document.getElementById("ttsStop");'
    'var rateSel=document.getElementById("ttsRate"),voiceSel=document.getElementById("ttsVoice");'
    'var state=document.getElementById("ttsState"),audio=document.getElementById("ttsAudio");'
    'var volEl=document.getElementById("ttsVol");'
    'var settingsEl=document.getElementById("ttsSettings");'
    'if(!group||!btn||!audio){if(group)group.hidden=true;return;}'
    'group.hidden=false;'
    'var rate=1,voice="",ready=false,lastUrl="";'
    'try{var sv=localStorage.getItem("dls_tts_rate");if(sv)rate=parseFloat(sv)||1;}catch(e){}'
    'try{voice=localStorage.getItem("dls_tts_voice")||"";}catch(e){}'
    'if(rateSel)rateSel.value=String(rate);'
    'if(volEl){try{var vv=localStorage.getItem("dls_tts_volume");if(vv!==null)volEl.value=vv;}catch(e){}'
    'audio.volume=(parseFloat(volEl.value)||100)/100;'
    'volEl.oninput=function(){audio.volume=(parseFloat(volEl.value)||0)/100;'
    'try{localStorage.setItem("dls_tts_volume",volEl.value);}catch(e){}};}'
    'function setState(s){if(state){state.textContent=s||"";state.title=s||"";}}'
    'function fname(){try{return new URLSearchParams(location.search).get("name")||"filer";}catch(e){return "filer";}}'
    'var zhVoice={"zh-CN-XiaoxiaoNeural":I18N["voice.xiaoxiao"],"zh-CN-XiaoyiNeural":I18N["voice.xiaoyi"],"zh-CN-YunxiNeural":I18N["voice.yunxi"],"zh-CN-YunjianNeural":I18N["voice.yunjian"],"zh-CN-YunxiaNeural":I18N["voice.yunxia"],"zh-CN-YunyangNeural":I18N["voice.yunyang"],"zh-HK-HiuGaaiNeural":I18N["voice.hiugaai"],"zh-HK-HiuMaanNeural":I18N["voice.hiumaan"],"zh-HK-WanLungNeural":I18N["voice.wanlung"],"zh-TW-HsiaoChenNeural":I18N["voice.hsiaochen"],"zh-TW-HsiaoYuNeural":I18N["voice.hsiaoyu"],"zh-TW-YunJheNeural":I18N["voice.yunjhe"]};'
    'function shortVoice(id,name){if(zhVoice[id])return zhVoice[id];'
    'var s=(name||id||"").replace(/^Microsoft\\s+/,"").replace(/\\s*\\(.*$/,"");'
    'return s.length>10?s.slice(0,10):s;}'
    'function url(){'
    'var v=(voiceSel&&voiceSel.value)||voice;'
    'if(window.TTS_URL){var p2=new URLSearchParams();p2.set("rate",String(rate));'
    'if(v)p2.set("voice",v);'
    'return window.TTS_URL+(window.TTS_URL.indexOf("?")>=0?"&":"?")+p2.toString();}'
    'var q=new URLSearchParams(location.search);'
    'var p=new URLSearchParams();'
    'p.set("dir",q.get("dir")||"/");p.set("name",q.get("name")||"");'
    'p.set("rate",String(rate));if(v)p.set("voice",v);'
    'return "/tts?"+p.toString();}'
    'function reset(){try{audio.pause();}catch(e){}'
    'audio.removeAttribute("src");audio.load();lastUrl="";'
    'btn.textContent=I18N["preview.read_aloud"];setState("");}'
    'function playIt(){'
    'if(!ready)return;'
    'var u=url();'
    'if(u!==lastUrl){lastUrl=u;audio.src=u;}'
    'setState(I18N["preview.generating"]);'
    'var pr=audio.play();'
    'if(pr&&pr.catch)pr.catch(function(e){'
    'if(e&&e.name==="AbortError"){setState("");btn.textContent=I18N["preview.read_aloud"];return;}'
    'setState(I18N["preview.play_failed"]+" "+(e.message||e));btn.textContent=I18N["preview.read_aloud"];});}'
    'btn.onclick=function(){'
    'if(!ready)return;'
    'if(!audio.src||audio.ended){playIt();return;}'
    'if(audio.paused){playIt();}else{audio.pause();}};'
    'stop.onclick=function(){reset();};'
    'audio.addEventListener("waiting",function(){setState(I18N["preview.generating"]);});'
    'audio.addEventListener("playing",function(){'
    'btn.textContent=I18N["preview.pause"];setState(I18N["preview.playing"]);'
    'if("mediaSession" in navigator){try{'
    'navigator.mediaSession.metadata=new MediaMetadata({title:fname(),artist:"filer"});'
    'navigator.mediaSession.setActionHandler("play",function(){audio.play();});'
    'navigator.mediaSession.setActionHandler("pause",function(){audio.pause();});'
    'navigator.mediaSession.setActionHandler("stop",function(){reset();});'
    '}catch(e){}}});'
    'audio.addEventListener("pause",function(){if(audio.ended)return;'
    'btn.textContent=I18N["preview.resume"];setState(I18N["preview.paused"]);});'
    'audio.addEventListener("ended",function(){btn.textContent=I18N[\'preview.read_aloud\'];setState("");lastUrl="";});'
    'audio.addEventListener("error",function(){if(!lastUrl)return;'
    'btn.textContent=I18N["preview.read_aloud"];setState(I18N["preview.generation_failed"]);});'
    'if(rateSel)rateSel.onchange=function(){'
    'rate=parseFloat(rateSel.value)||1;'
    'try{localStorage.setItem("dls_tts_rate",String(rate));}catch(e){}'
    'if(audio&&!audio.paused)playIt();};'
    'if(voiceSel)voiceSel.onchange=function(){'
    'voice=voiceSel.value;'
    'try{localStorage.setItem("dls_tts_voice",voice);}catch(e){}'
    'if(audio&&!audio.paused)playIt();};'
    'fetch("/tts/voices",{headers:{"Accept":"application/json"}})'
    '.then(function(r){if(!r.ok)throw new Error("HTTP "+r.status);return r.json();})'
    '.then(function(j){'
    'if(!j||!j.ok)throw new Error((j&&j.error)||I18N["preview.voice_service_unavailable"]);'
    'if(voiceSel){voiceSel.innerHTML="";'
    'var list=j.voices||[];'
    'for(var i=0;i<list.length;i++){var o=document.createElement("option");'
    'o.value=list[i].id;o.textContent=shortVoice(list[i].id,list[i].name);o.title=list[i].name||list[i].id;'
    'voiceSel.appendChild(o);}'
    'if(!list.length){var o2=document.createElement("option");'
    'o2.value=j.default||"";o2.textContent=I18N["preview.default_voice"];voiceSel.appendChild(o2);}'
    'if(voice){voiceSel.value=voice;if(voiceSel.value!==voice)voiceSel.value=j.default||"";}'
    'else if(j.default){voiceSel.value=j.default;}'
    'voice=voiceSel.value||"";}'
    'if(settingsEl)settingsEl.hidden=false;'
    'ready=true;setState("");'
    '})'
    '.catch(function(e){ready=false;if(settingsEl)settingsEl.hidden=true;'
    'setState(I18N["preview.voice_unavailable"]+" "+(e.message||e));'
    'btn.disabled=true;if(stop)stop.disabled=true;});'
    '})();'
)


_BROWSE_TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{FILENAME}} - {{i18n:app.title}}</title>
<style>
*{box-sizing:border-box;}
body{margin:0;font-family:''' + FONT_STACK + ''';background:#f1f5f9;color:#1e293b;}
.topbar{position:sticky;top:0;z-index:10;background:#0f172a;color:#e2e8f0;padding:10px 16px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.topbar .ttl{font-weight:600;font-size:15px;word-break:break-all;}
.mid{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-left:auto;}
button{font:inherit;}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:4px;height:var(--h-ctl);padding:0 var(--px-ctl);border-radius:var(--radius);font-size:var(--font-ui);border:1px solid #475569;color:#e2e8f0;background:#1e293b;text-decoration:none;cursor:pointer;box-sizing:border-box;white-space:nowrap;}
.btn:hover{background:#334155;}
.btn-dl{color:#fbd38d;border-color:#b7791f;background:#7c2d12;}
.btn-dl:hover{background:#92400e;}
.btn-prev{color:#c4b5fd;border-color:#6d28d9;background:#2e1065;}
.btn-prev:hover{background:#3b0d7a;}
.btn-del{color:#fecaca;border-color:#b91c1c;background:#450a0a;}
.btn-del:hover{background:#7f1d1d;}
{{INFO_CSS}}
.actions{display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.act-form{display:inline-flex;align-items:center;margin:0;}
.topbar .actions .btn{width:var(--h-icon);height:var(--h-icon);padding:0;justify-content:center;}
.topbar .btn svg{width:var(--icon);height:var(--icon);display:block;}
.frame{height:calc(100vh - 62px);}
iframe{width:100%;height:100%;border:0;background:#fff;display:block;}
@media(max-width:640px){.frame{height:calc(100vh - 104px);}.btn{flex:1 1 96px;}}
</style>
</head>
<body>
<div class="topbar">
  <span class="ttl">📄 {{FILENAME}}</span>
  <div class="mid">
    <a class="btn" href="{{FALLBACK}}" onclick="if(history.length&gt;1){event.preventDefault();history.back();return false;}">{{i18n:preview.back_previous}}</a>
    <div class="actions">{{ACTION_PREVIEW}}{{ACTION_DOWNLOAD}}{{ACTION_DELETE}}</div>
  </div>
</div>
<div class="frame"><iframe src="{{SRC}}" title="{{FILENAME}}"></iframe></div>
</body>
</html>'''


# 简笔画线条图标（24x24 stroke 风格，颜色跟随 currentColor）
_ICON_OPEN = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<path d="M6 17l2-5h14l-2 6a2 2 0 0 1-2 1H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h4l2 2h10a2 2 0 0 1 2 2v1"/></svg>')
_ICON_PREVIEW = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
                 '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>')
_ICON_EDIT = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>')
_ICON_DL = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
            '<polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>')
_ICON_DEL = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" '
             'stroke-linecap="round" aria-hidden="true">'
             '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>')
_ICON_HELP = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>'
              '<line x1="12" y1="17" x2="12.01" y2="17"/></svg>')
_ICON_INFO = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<circle cx="12" cy="12" r="10"/><line x1="12" y1="11" x2="12" y2="17"/>'
              '<line x1="12" y1="7" x2="12.01" y2="7"/></svg>')

# 文件信息弹窗：样式 / 结构 / 脚本（列表页与浏览页共用）
_INFO_CSS = (
    '.infomodal{position:fixed;inset:0;background:rgba(15,23,42,.45);z-index:900;'
    'display:flex;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;}'
    '.infomodal[hidden]{display:none;}'
    '.infocard{background:#fff;border-radius:12px;box-shadow:0 10px 40px rgba(0,0,0,.25);'
    'width:min(540px,92vw);padding:18px 22px;box-sizing:border-box;max-height:86vh;overflow:auto;}'
    '.infohead{display:flex;align-items:center;justify-content:space-between;'
    'font-weight:600;font-size:15px;color:#1e3a5f;margin-bottom:10px;}'
    '.info-close{border:none;background:#f1f5f9;border-radius:var(--radius);width:var(--h-icon);height:var(--h-icon);'
    'cursor:pointer;font-size:var(--font-ui);color:#64748b;}'
    '.info-close:hover{background:#e2e8f0;color:#b91c1c;}'
    '.info-row{display:flex;align-items:center;gap:12px;padding:7px 0;border-bottom:1px solid #f1f5f9;font-size:var(--font-ui);}'
    '.info-row:last-child{border-bottom:none;}'
    '.ik{flex:0 0 76px;color:#64748b;}'
    '.iv{flex:1;min-width:0;word-break:break-all;color:#0f172a;}'
    '.btn-info{color:#0f766e;background:#f0fdfa;border-color:#99f6e4;}'
    '.btn-info:hover{background:#ccfbf1;border-color:#5eead4;}'
    '.legend .lg-info{color:#0f766e;}'
)
_INFO_MODAL = (
    '<div class="infomodal" id="infoModal" hidden>'
    '<div class="infocard">'
    '<div class="infohead">📋 {{i18n:dialog.info.title}}<button class="info-close" id="infoClose" type="button" title="{{i18n:common.close}}">✕</button></div>'
    '<div>'
    '<div class="info-row"><span class="ik">{{i18n:dialog.info.name}}</span><span class="iv" id="iv_name"></span></div>'
    '<div class="info-row"><span class="ik">{{i18n:dialog.info.location}}</span><span class="iv" id="iv_dir"></span></div>'
    '<div class="info-row"><span class="ik">{{i18n:dialog.info.type}}</span><span class="iv" id="iv_type"></span></div>'
    '<div class="info-row"><span class="ik">{{i18n:dialog.info.size}}</span><span class="iv" id="iv_size"></span></div>'
    '<div class="info-row"><span class="ik">{{i18n:dialog.info.mtime}}</span><span class="iv" id="iv_mtime"></span></div>'
    '<div class="info-row"><span class="ik">{{i18n:dialog.info.ctime}}</span><span class="iv" id="iv_ctime"></span></div>'
    '<div class="info-row"><span class="ik">{{i18n:dialog.info.permissions}}</span><span class="iv" id="iv_perm"></span></div>'
    '<div class="info-row"><span class="ik">{{i18n:dialog.info.access}}</span><span class="iv" id="iv_rw"></span></div>'
    '</div></div></div>'
)
_INFO_JS = (
    'var infoModal=document.getElementById("infoModal");'
    'var infoClose=document.getElementById("infoClose");'
    'if(infoClose)infoClose.onclick=function(){infoModal.hidden=true;};'
    'if(infoModal)infoModal.addEventListener("mousedown",function(e){if(e.target===infoModal)infoModal.hidden=true;});'
    'function showInfo(b){'
    'var dir=b.getAttribute("data-dir")||"/",name=b.getAttribute("data-name")||"";'
    'fetch("/info?"+new URLSearchParams({dir:dir,name:name}),{headers:{Accept:"application/json"}})'
    '.then(function(r){return r.json();})'
    '.then(function(j){'
    'if(!j||!j.ok){alert((j&&j.error)||I18N["dialog.info.fetch_failed"]);return;}'
    'document.getElementById("iv_name").textContent=j.name;'
    'document.getElementById("iv_dir").textContent=j.dir;'
    'document.getElementById("iv_type").textContent=j["type"];'
    'document.getElementById("iv_size").textContent=I18N["dialog.info.size_value"].replace("{human}",j.size_human).replace("{n}",j.size);'
    'document.getElementById("iv_mtime").textContent=j.mtime;'
    'document.getElementById("iv_ctime").textContent=j.ctime;'
    'document.getElementById("iv_perm").textContent=j.perm+"（"+j.perm_str+"）";'
    'document.getElementById("iv_rw").textContent=I18N["dialog.info.access_value"].replace("{r}",j.readable?I18N["dialog.info.readable"]:I18N["dialog.info.unreadable"]).replace("{w}",j.writable?I18N["dialog.info.writable"]:I18N["dialog.info.unwritable"]);'
    'infoModal.hidden=false;'
    '}).catch(function(e){alert(I18N["dialog.info.request_failed"].replace("{error}",e));});'
    '}'
)


_BROWSE_TEMPLATE = _BROWSE_TEMPLATE.replace('{{INFO_CSS}}', _INFO_CSS)

for _name in (
    '_PREVIEW_TEMPLATE', '_TEXT_PREVIEW_TEMPLATE', '_DOC_PREVIEW_TEMPLATE',
    '_ARTICLE_TEMPLATE', '_PDF_PREVIEW_TEMPLATE', '_PAGES_PREVIEW_TEMPLATE',
    '_WRAP_TEMPLATE', '_EDIT_TEMPLATE', '_BROWSE_TEMPLATE',
):
    _tpl = globals()[_name].replace('<style>', '<style>' + BASE_CSS, 1)
    globals()[_name] = _tpl
