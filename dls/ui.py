BASE_CSS = """
:root{
  --h-ctl: 32px;
  --h-ctl-sm: 26px;
  --h-icon: 32px;
  --px-ctl: 12px;
  --gap: 8px;
  --gap-lg: 12px;
  --radius: 6px;
  --radius-pill: 999px;
  --icon: 16px;
  --font-ui: 13px;
}
.btn, button.btn, .tbtn, .tsel, .shkey{
  height: var(--h-ctl);
  padding: 0 var(--px-ctl);
  font-size: var(--font-ui);
  border-radius: var(--radius);
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  line-height: 1;
  cursor: pointer;
}
input[type=text], input[type=search], input[type=password], select{
  height: var(--h-ctl);
  padding: 0 var(--px-ctl);
  font-size: var(--font-ui);
  border-radius: var(--radius);
  box-sizing: border-box;
}
.btn svg, .tbtn svg, .shkey svg{ width: var(--icon); height: var(--icon); }
"""

FONT_STACK = (
    'system-ui,-apple-system,"Segoe UI","PingFang SC",'
    '"Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC",sans-serif'
)
