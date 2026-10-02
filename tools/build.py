"""Build a dependency-free, multi-page source book from editable content."""
from pathlib import Path
from html import escape as esc
import json, shutil, re, hashlib, zipfile
from book_content import CHAPTERS, CANDIDATES
ROOT=Path(__file__).resolve().parents[1];DIST=ROOT/'dist'
CASES=json.loads((ROOT/'content/cases.json').read_text())
GUIDES=json.loads((ROOT/'content/reading-guides.json').read_text())
RESEARCH={r['id']:r for r in json.loads((ROOT/'content/research.json').read_text())}

def p(text):return ''.join('<p>'+esc(s)+'</p>' for s in text.split('\n\n') if s)
def link(path,text):return '<a href="'+esc(path,quote=True)+'">'+esc(text)+'</a>'
def case_link(slug,text=None):return link('cases/'+slug+'.html',text or next(c['title'].split(' · ')[0] for c in CASES if c['id']==slug))
def table(rows):
    return '<div class="table-scroll" tabindex="0"><table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in rows[0])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(str(x))+'</td>' for x in r)+'</tr>' for r in rows[1:])+'</tbody></table></div>'
def flow(items):return '<ol class="flow" aria-label="执行流程">'+''.join('<li><span>'+str(i+1).zfill(2)+'</span>'+esc(x)+'</li>' for i,x in enumerate(items))+'</ol><p class="caption">教学路径示意；表示本章阅读顺序，不是动态调用图。</p>'
def qa(items):return ''.join('<div class="checkpoint"><p class="question">'+esc(q)+'</p><details><summary>对照参考答案</summary>'+p(a)+'</details></div>' for q,a in items)

def reading_guide(guide,title):
    body='<section id="reading-task" class="reading-task"><h2>'+esc(title)+'</h2>'+p(guide['goal'])
    body+='<p class="caption">读前准备：'+esc(guide['prerequisites'])+'</p>'
    body+='<ol class="reading-steps">'+''.join('<li>'+esc(step)+'</li>' for step in guide['steps'])+'</ol>'
    body+='<div class="checkpoint"><p class="question">'+esc(guide['verification'])+'</p><details><summary>查看判断标准</summary>'+p(guide['expected'])+'</details></div></section>'
    return body

def markdown_sections(items):
    lines=[]
    for s in items:
        lines+=['### '+s['title'],'']
        for paragraph in s.get('paragraphs',[]):lines+=[paragraph,'']
        if s.get('flow'):lines+=[' → '.join(s['flow']),'']
        if s.get('table'):
            rows=s['table'];lines+=['| '+' | '.join(rows[0])+' |','| '+' | '.join(['---']*len(rows[0]))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows[1:]]+['']
        if s.get('code'):lines+=[s.get('codeLabel','教学示例'),'','```python',s['code'],'```','']
        for q,a in s.get('questions',[]):lines+=['预测：'+q,'','参考：'+a,'']
    return lines

def markdown_guide(guide,title):
    return ['### '+title,'',guide['goal'],'','读前准备：'+guide['prerequisites'],'']+[str(i+1)+'. '+step for i,step in enumerate(guide['steps'])]+['','检验理解：'+guide['verification'],'','判断标准：'+guide['expected'],'']

NAV=[('index.html','导读 · 从问题进入源码','导读')]+[(x['id']+'.html',x['number']+' '+x['title'],'工程主线') for x in CHAPTERS]+[('cases/'+x['id']+'.html',x['title'].split(' · ')[0],'源码案例') for x in CASES]+[(x+'.html',title,'研究附录') for x,title in [('comparison','跨项目比较'),('labs','四个教学实验'),('candidates','还值得拆解哪些项目'),('sources','版本、来源与证据')]]
SEARCH=[dict(title=t,url=u,text=t) for u,t,_ in NAV]
for c in CASES:
    for x in c['concepts']:
        SEARCH.append(dict(title=c['title'].split(' · ')[0]+' / '+x['name'],url='cases/'+c['id']+'.html#'+x['id'],text=x['explanation'][:240]))

def render(route,title,subtitle,body,toc,kind='工程主线'):
    depth=route.count('/');prefix='../'*depth
    # Rebase only local links so the same content works online and in a downloaded folder.
    body=re.sub(r'href="(?!https?:|#|mailto:)([^"]+)"',lambda m:'href="'+prefix+m[1]+'"',body)
    nav='';last=None
    for u,t,g in NAV:
        if g!=last:nav+='<p class="nav-group">'+g+'</p>';last=g
        nav+='<a'+(' aria-current="page" class="active"' if u==route else '')+' href="'+prefix+u+'">'+esc(t)+'</a>'
    pos=next(i for i,x in enumerate(NAV) if x[0]==route)
    adjacent='<nav class="adjacent" aria-label="相邻章节">'
    if pos:adjacent+=link(prefix+NAV[pos-1][0],'← '+NAV[pos-1][1])
    if pos<len(NAV)-1:adjacent+=link(prefix+NAV[pos+1][0],NAV[pos+1][1]+' →')
    adjacent+='</nav>'
    toc_html=''.join(link('#'+sid,name) for sid,name in toc)
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)} · Agent 工程拆解</title><meta name="description" content="{esc(subtitle,quote=True)}"><link rel="icon" href="{prefix}assets/favicon.svg"><link rel="stylesheet" href="{prefix}assets/book.css"><script src="{prefix}assets/book.js" defer></script></head><body data-root="{prefix}">
<a class="skip" href="#reading">跳到正文</a><header class="mobile-bar"><a href="{prefix}index.html">Agent 工程拆解</a><button id="menu-toggle" aria-controls="book-nav" aria-expanded="false">目录</button></header><div id="nav-shade" hidden></div>
<aside id="book-nav" aria-label="全书目录"><a class="brand" href="{prefix}index.html"><span class="brand-symbol">A<span>→</span></span><strong>Agent 工程拆解</strong><small>沿真实源码，理解执行与状态</small></a><label for="book-search">搜索章节或概念</label><input id="book-search" type="search" placeholder="试试：恢复、工具、记忆" autocomplete="off"><div id="search-results" aria-live="polite"></div><nav>{nav}</nav><p class="nav-foot">第一版 · 2026.10.02<br>12 个案例 · 179 个概念</p></aside>
<div class="page"><div class="reading-grid"><main id="reading"><div class="reading-top"><span>{esc(kind)}</span><div class="text-size" aria-label="正文大小"><button id="font-down" aria-label="缩小正文">A−</button><button id="font-up" aria-label="放大正文">A＋</button></div></div><h1>{esc(title)}</h1><p class="dek">{esc(subtitle)}</p>{body}{adjacent}<footer>这是固定版本的源码教材。观察、推断与运行证据分别标注。<br>{link(prefix+'sources.html','查看来源与适用边界')} · {link(prefix+'downloads/agent-engineering-book.md','下载整本 Markdown')}</footer></main><aside class="toc" aria-label="本页目录"><p>本页内容</p>{toc_html}</aside></div></div></body></html>'''

def write_page(route,title,subtitle,body,toc,kind='工程主线'):
    dest=DIST/route;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(render(route,title,subtitle,body,toc,kind))

def sections(sections):
    body='';toc=[]
    for i,s in enumerate(sections):
        sid='s'+str(i+1);toc.append((sid,s['title']));body+=f'<section id="{sid}"><h2>{esc(s["title"])}</h2>'
        body+=''.join(p(t) for t in s.get('paragraphs',[]))
        if s.get('flow'):body+=flow(s['flow'])
        if s.get('table'):body+=table(s['table'])
        if s.get('code'):body+='<p class="caption">'+esc(s.get('codeLabel','教学示例'))+'</p><pre><code>'+esc(s['code'])+'</code></pre>'
        if s.get('questions'):body+=qa(s['questions'])
        body+='</section>'
    return body,toc

def build():
    DIST.mkdir(exist_ok=True);(DIST/'assets').mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'content/book.css',DIST/'assets/book.css')
    js=(ROOT/'content/book.js').read_text().replace('BOOK_SEARCH_DATA',json.dumps(SEARCH,ensure_ascii=False).replace('</','<\\/'))
    (DIST/'assets/book.js').write_text(js)
    (DIST/'assets/favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="10" fill="#122b36"/><path d="M12 13h10c3 0 4 2 4 4v20c-2-3-6-4-14-4zM36 13H26v24c2-3 6-4 10-4z" fill="none" stroke="#71d2bf" stroke-width="2"/></svg>')
    intro=[
      dict(title='回答生成之后，任务才刚开始',paragraphs=[
       '模型返回一段文字之后，程序还要判断：动作是否获准，执行结果属于哪次调用，页面变化后旧动作能否继续，重启后应采用哪份状态。本书沿固定版本的源码追踪这些问题，帮助你解释任务如何执行、失败和恢复。',
       '十章主线介绍工程概念，十二个案例提供具体源码路径。你可以先读相关主线，再进入案例；原八份学习包的 52 章交互课程也可继续使用。新增四个案例补充执行交接、代码动作、长期记忆和浏览器行动。全书 179 个概念均有固定版本源码和预测题。'],flow=['目标与输入','上下文装配','模型提案','工具与执行','观察与状态','终态与评测']),
      dict(title='怎样使用这本书',paragraphs=[
       '先选一个具体问题，例如“重复事件为什么把完成状态改回运行中”。读主线认识术语和责任，进入案例定位源码；写下状态预测后，再展开参考答案。最后换一个输入，检验自己的解释是否仍成立。',
       '有 Go 背景可以先读 Eino；想理解编码 Agent 可从 mini-SWE-agent 与 Pi 开始；关注记忆则从第 2、5 章进入 Letta Code；要建立评测从第 7 章和 Inspect AI 开始。'],table=[['你想解决的问题','先读主线','再看案例'],['一次任务如何跑完','01 / 03','mini-SWE-agent、smolagents、Agents SDK'],['长任务为何丢上下文','02 / 05 / 06','Pi、Codex、Letta Code'],['并发与恢复如何正确','04 / 06','LangGraph、Eino、OpenHands、DeerFlow'],['怎样证明任务完成','07 / 08','Inspect AI、browser-use']]),
      dict(title='这本书的证据边界',paragraphs=[
       '源码观察给出局部结构与分支；跨项目比较是本书的研究判断；教学模型只验证明确建模的契约。原 Eino 的六案例使用真实框架与脚本模型；新增四项目没有执行真实模型、Cloud 或浏览器任务。每个案例单独列出排除范围。',
       '本书借鉴李博杰《深入理解 AI Agent》以工程问题组织学习的思路，正文、案例编排与练习独立撰写。引用框架源码时保留版本、连续行号和许可；不以仓库星数替代研究价值。']),
      dict(title='先从一条路径读起',paragraphs=['第一次阅读可以从第 1 章和 mini-SWE-agent 开始。每章开头给出阅读任务与判断标准；先写预测，再核对源码。读完后合上正文，画出模型、环境、消息和终态之间的关系，并用一个失败样例解释观察怎样回到下一轮输入。'])]
    body,toc=sections(intro);body+='<p class="start-reading">'+link('runtime.html','开始第 1 章：执行循环 →')+'</p>'
    body+='<p class="caption">方法参考：'+link('https://github.com/bojieli/ai-agent-book','bojieli/ai-agent-book')+'；本书不是该项目的官方版本。</p>'
    write_page('index.html','从一次任务，读懂 Agent 工程','一本围绕执行、上下文、工具、记忆、恢复和评测的源码拆解书。',body,toc,'导读')
    for ch in CHAPTERS:
        body,toc=sections(ch['sections']);body=reading_guide(GUIDES['chapters'][ch['id']],'本章阅读任务')+body;toc.insert(0,('reading-task','本章阅读任务'))
        body+='<section id="cases"><h2>沿源码继续读</h2><p>'+ ' · '.join(case_link(x) for x in ch['cases'])+'</p></section>';toc.append(('cases','沿源码继续读'))
        write_page(ch['id']+'.html',ch['number']+' · '+ch['title'],ch['subtitle'],body,toc)
    for c in CASES:
        body=reading_guide(GUIDES['cases'][c['id']],'本案例阅读任务')+'<section id="map"><h2>先把主线画出来</h2>'+p(c['question'])+flow(c['journey'])
        body+='<div class="evidence"><strong>证据范围</strong>'+p(c.get('runtime') or '静态教材；未报告上游运行结果。')+p(c.get('warning',''))+'</div></section>'
        if c.get('course'):
            body+='<p class="start-reading">'+link('courses/'+c['id']+'/index.html','进入原 '+str(len(c['originalModules']))+' 章交互课程 →')+'</p>'
        body+='<section id="version"><h2>版本与阅读边界</h2><p>'+link(c['repository'],c['repository'].replace('https://github.com/',''))+' · 访问 '+c['accessDate']+'</p><details><summary>查看完整提交与排除范围</summary><p><code>'+c['revision']+'</code></p>'+p('；'.join(c['excluded']))+'</details><p class="caption">阅读路径：'+esc(' → '.join(dict.fromkeys(c['reading'])))+'</p></section>'
        toc=[('reading-task','本案例阅读任务'),('map','主线与证据'),('version','版本与边界')]
        for i,x in enumerate(c['concepts']):
            toc.append((x['id'],str(i+1).zfill(2)+' '+x['name']))
            body+=f'<section id="{x["id"]}" class="concept"><p class="concept-number">概念 {i+1:02d}</p><h2>{esc(x["name"])}</h2><p class="outcome">{esc(x["outcome"])}</p>'
            if x.get('requires'):body+='<p class="caption">先修：'+ ' · '.join(link('cases/'+c['id']+'.html#'+r,next((z['name'] for z in c['concepts'] if z['id']==r),r)) for r in x['requires'])+'</p>'
            body+=p(x['explanation'])
            for a in x['anchors']:
                start,end=a['lines'].split('-');url=c['repository']+'/blob/'+c['revision']+'/'+a['path']+'#L'+start+'-L'+end
                body+='<details class="source"><summary>读源码 · '+esc(a['path']+':'+a['lines'])+'</summary><p class="caption">源码观察：'+esc(a.get('claim',''))+'</p><pre><code>'+esc(a['text'])+'</code></pre><p>'+link(url,'查看基础提交中的文件 ↗')+'</p>'
                if c['id']=='deer-flow':body+='<p class="caption">此案例含本地工作区修改；上方逐字快照与文件哈希是引用依据，远端基础提交可能有差异。</p>'
                body+='</details>'
            body+=qa([(q['prompt'],q['answer']) for q in x.get('checkpoints',[])])+'</section>'
        guide=GUIDES['cases'][c['id']]
        body+='<section id="teach-back"><h2>闭卷复述与迁移</h2>'+p('合上源码，回答本案例开头的阅读问题：'+guide['verification'])+p('用一张路径图说明输入、执行者、状态和终止原因，再提出一个新样例，写出预测、源码依据和仍需真实运行的条件。')+'</section>';toc.append(('teach-back','闭卷复述与迁移'))
        write_page('cases/'+c['id']+'.html',c['title'],'围绕一个具体工程问题，逐段读源码、解释契约并预测失败。',body,toc,'源码案例')
    comparison=[['项目','执行/状态焦点','最有价值的比较点','当前运行证据']]
    focus={'mini-swe-agent':'线性步骤 / trajectory','pi':'Agent loop / 活动会话树','langgraph':'superstep / checkpoint','eino':'类型图 / 消息流 / ADK','openhands':'Conversation / 事件树','deer-flow':'Gateway Runtime / 工具账本 / 回放','inspect-ai':'Task / Solver / Scorer','codex':'压缩窗口 / rollout 恢复','openai-agents-python':'NextStep / handoff / RunState','smolagents':'代码动作 / ActionStep','letta-code':'记忆作用域 / 投影 / Git 边界','browser-use':'页面观察 / 动作批次 / done'}
    for c in CASES:comparison.append([c['title'].split(' · ')[0],focus[c['id']],c.get('warning') or c['question'],c['runtime']])
    body,toc=sections([dict(title='按工程问题比较，不按品牌排队',paragraphs=['下表是本书对冻结版本的比较。一个框架没有出现在某个主题，不代表它缺少该能力；可能只是本次阅读范围没有覆盖。版本、模型、环境和评测口径不同，不能由这些案例推出性能排名。'],table=comparison),dict(title='共同问题，不同身份',paragraphs=['事件游标、图 checkpoint、会话 leaf、当前 Agent、记忆提交和压缩窗口都有自己的身份。首先写出项目的保存与恢复对象，再比较差异。', '选择工程实现时，先明确你需要解决的失败：若主要是动作生成，从最小循环出发；若主要是状态合并，研究图；若主要是持久会话，研究事件与投影；若主要是任务成败，先建立评测。框架选择是这些约束的结果。'])])
    write_page('comparison.html','十二个案例，怎样互相对照','同一个问题回到不同源码，形成可迁移的判断。',body,toc,'研究附录')
    body,toc=sections([dict(title='实验都能离线运行',paragraphs=['四个实验使用本书独立的 Python 模型，不导入上游库，不调用模型 API，不修改外部系统。它们分别检验终态保护、页面过期动作、记忆投影和评测分母。结果只说明这些教学契约，不能替代真实框架运行。'],code='python3 tools/labs.py --output verification/labs.json',codeLabel='在书稿目录运行；Python 3.10+'),dict(title='每个实验先写预测',table=[['实验','输入与正确策略','错误策略 / 反例'],['工具账本','同一 call_id 位于不同 run，终态后收到 started','只按 call_id 去重；迟到事件降级终态'],['浏览器动作批次','第一个动作改变页面焦点，剩余动作停止','继续执行旧观察下的第二个动作'],['记忆投影','v2 嵌套目录每层都提供 MEMORY.md','缺少中间索引；skills 独立处理'],['评测分母','计划 5、运行 4、评分 2、正确 1','把未评分计为错误，隐藏未运行']]),dict(title='从教学模型转入真实项目',paragraphs=['先保持输入和判据不变，再用对应项目接口替换模型。新增证据应记录真实库提交、运行环境、日志和失败；不要覆盖旧教学结果。', '下载随书实验源码后，先读文件顶部的范围声明。它们的作用是帮助你预测和解释一个契约，不是重建完整 Agent Runtime。'])])
    body+='<p>'+link('downloads/labs.py','下载四个实验源码')+'</p>'
    write_page('labs.html','四个可重复的教学实验','用固定输入比较正确策略与常见错误。',body,toc,'研究附录')
    body=p('以下优先级是本书根据能力互补、可追踪源码、可缩小的实验范围、运行成本与维护状态作出的研究判断。均已读取官方 README 和仓库元数据；尚未完成源码案例，不计入十二个已拆解项目。')
    toc=[]
    for i,(slug,title,priority,topic,value,next_step) in enumerate(CANDIDATES):
        r=RESEARCH[slug];sid='c'+str(i+1);toc.append((sid,title));body+=f'<section id="{sid}"><p class="concept-number">{i+1:02d} · {priority}</p><h2>{esc(title)}</h2>'+p(topic+'。'+value)+p('下一次拆解：'+next_step)+'<p>'+link(r['html_url'],'官方仓库 ↗')+'</p><p class="caption">核对 '+r['accessDate']+'；仓库最近 pushed_at '+r['pushed_at']+'。README 快照与元数据只证明该日可见说明，不能替代运行或许可审查。</p></section>'
    write_page('candidates.html','还值得加入分析的十个项目','先补评测、隔离与类型契约，再扩展更多编排框架。',body,toc,'研究附录')
    rows=[['案例','冻结提交','访问日期','来源与许可']]
    for c in CASES:rows.append([c['title'].split(' · ')[0],c['revision'],c['accessDate'],c.get('license','见随书上游许可')])
    body,toc=sections([dict(title='固定版本与来源',paragraphs=['原八案例采用先前教材冻结的源码。新增四案例于 2026-10-02 获取公开仓库，冻结完整提交，并逐字检查所有概念锚点。DeerFlow 采用本地 fork 加工作区快照，不能把基础提交误当成全部本地内容。'],table=rows),dict(title='证据分级与未验证范围',paragraphs=['源码摘录使用仓库相对路径、一基连续行号、逐字文本和文件 SHA-256。每个概念的解释可能包含教学推理；局部结构观察不自动成为完整动态调用图。', '新增四项目只完成有边界的源码阅读，没有执行真实模型、Cloud、账号鉴权、远程沙箱或生产并发。原八项目的已有运行证据按各案例范围引用，本次书籍构建不升级其等级。独立教学实验也不证明生产行为。', '没有真实学习者作答，本书验收的是教材可用性与证据可追溯性；不声称读者已经掌握。']),dict(title='方法参考与上游权利',paragraphs=['方法参考：李博杰的 ai-agent-book，以工程主题连接设计原理和实践。本书按十二个真实项目的执行路径独立撰写，没有复制参考书正文、实验或插图。', '书中短源码摘录及原课程引用保留上游许可；各项目代码权利仍属于原作者与贡献者。随书提供上游 LICENSE / NOTICE 文件，具体使用应看对应目录条款。Mastra 等候选仅链接研究，未复制其企业实现。']),dict(title='可下载的材料',paragraphs=['Markdown 是可检索的全书正文；离线包包含多页阅读站点和原八交互课程；来源清单包含概念、源码范围与哈希，不包含本机路径、密钥或账户材料。'])])
    body+='<p>'+link('https://github.com/bojieli/ai-agent-book','参考书官方仓库')+'</p><ul><li>'+link('downloads/agent-engineering-book.md','整本 Markdown')+'</li><li>'+link('downloads/agent-engineering-book-offline.zip','离线阅读包')+'</li><li>'+link('downloads/source-map.json','概念与源码来源清单')+'</li></ul>'
    for c in CASES:
        lp=ROOT/'content/licenses'/c['id']
        for f in lp.glob('*'):body+='<p>'+link('licenses/'+c['id']+'/'+f.name,c['title'].split(' · ')[0]+' / '+f.name)+'</p>'
    write_page('sources.html','版本、来源与证据','准确说明读过什么、运行过什么，以及尚未证明什么。',body,toc,'研究附录')
    for f in (ROOT/'content/courses').glob('*.html'):
        slug=f.stem;dest=DIST/'courses'/slug/'index.html';dest.parent.mkdir(parents=True,exist_ok=True)
        back='<a href="../../cases/'+slug+'.html" style="position:fixed;right:18px;bottom:18px;z-index:1000;background:#12333d;color:#fff;padding:10px 16px;border-radius:6px;font:14px sans-serif;text-decoration:none">← 返回在线书</a>'
        html=f.read_text().replace('</body>',back+'</body>')
        if '<title>' in html:html=html.replace('</head>','<link rel="icon" href="../../assets/favicon.svg"></head>')
        dest.write_text(html)
        aux=ROOT/'content/course-licenses'/slug
        if aux.exists():
            for f in aux.iterdir():shutil.copyfile(f,dest.parent/f.name)
    shutil.copytree(ROOT/'content/licenses',DIST/'licenses',dirs_exist_ok=True)
    (DIST/'downloads').mkdir(exist_ok=True)
    (DIST/'downloads/source-map.json').write_text(json.dumps(CASES,ensure_ascii=False,indent=2)+'\n')
    shutil.copyfile(ROOT/'tools/labs.py',DIST/'downloads/labs.py')
    md=export_markdown(intro);(ROOT/'BOOK.md').write_text(md);(DIST/'downloads/agent-engineering-book.md').write_text(md)
    manifest=dict(date='2026-10-02',bookPages=len(NAV),cases=len(CASES),concepts=sum(len(c['concepts']) for c in CASES),originalInteractiveChapters=sum(len(c.get('originalModules',[])) for c in CASES),candidateProjects=len(CANDIDATES),pages=[x[0] for x in NAV])
    (DIST/'book-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    # Do not recursively include the archive itself.
    archive=DIST/'downloads/agent-engineering-book-offline.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(DIST.rglob('*')):
            if f.is_file() and f!=archive:z.write(f,'agent-engineering-book/'+f.relative_to(DIST).as_posix())
    print(json.dumps(manifest,ensure_ascii=False))

def export_markdown(intro):
    lines=['# Agent 工程拆解','', '第一版 · 2026-10-02 · 十二案例、十章工程主线。', '', '方法参考：https://github.com/bojieli/ai-agent-book 。正文、案例与练习独立撰写。', '', '证据边界：源码观察、研究推断、独立模型与真实框架运行分别记录。新增四项目未运行真实模型或外部服务。','']
    lines+=['## 导读','']+markdown_sections(intro)
    for ch in CHAPTERS:
        lines+=['## '+ch['number']+' · '+ch['title'],'',ch['subtitle'],'']
        lines+=markdown_guide(GUIDES['chapters'][ch['id']],'本章阅读任务')+markdown_sections(ch['sections'])
    for c in CASES:
        lines+=['## '+c['title'],'',c['question'],'','来源：'+c['repository'],'', '提交：`'+c['revision']+'`；访问：'+c['accessDate'],'', '证据：'+c['runtime'],'',c.get('warning',''),'','排除：'+'；'.join(c['excluded']),'']
        lines+=markdown_guide(GUIDES['cases'][c['id']],'本案例阅读任务')+['阅读主线：'+' → '.join(c['journey']),'']
        for x in c['concepts']:
            lines+=['### '+x['name'],'',x['explanation'],'']
            for a in x['anchors']:
                lines+=['源码观察：'+a['claim'],'','`'+a['path']+':'+a['lines']+'`','', '```',a['text'],'```','']
            for q in x.get('checkpoints',[]):lines+=['预测：'+q['prompt'],'','参考：'+q['answer'],'']
        lines+=['### 闭卷复述与迁移','',GUIDES['cases'][c['id']]['verification'],'','请用路径图和一个新输入说明预测、源码依据及未验证条件。','']
    lines+=['## 后续候选与边界','']
    for slug,title,priority,topic,value,next_step in CANDIDATES:
        lines+=['### '+title+' · '+priority,'',topic+'。'+value,'','下一次拆解：'+next_step,'',RESEARCH[slug]['html_url'],'', '当前仅核对官方 README 与元数据；未计入已完成源码案例。','']
    return '\n'.join(lines)

if __name__=='__main__':build()
