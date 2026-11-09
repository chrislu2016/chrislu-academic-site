"""经济工作年鉴 · 数据构建脚本

用法：python3 scripts/build.py --src <原始材料目录>
输出：data/corpus.json（全文，按句）  data/site.json（页面所需的全部结构化数据）

每年更新：
  1. 把新一年的会议通稿 docx 放进 <src>/当前/数据/99_原有数据包/数据/中央经济工作会议/
     把新一年的政府工作报告 md 放进 <src>/重做_概念史/数据/政府工作报告/
  2. 运行本脚本；新年份的重点任务会自动切分，检查后写入 scripts/tasks_curated.json
  3. 在 scripts/terms.json 里补充当年的新提法（人工判断），在 scripts/milestones.json 里补充信息观念的转折性表述，再运行一次
"""
import argparse, glob, json, os, re, zipfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'data')
ORD = '一二三四五六七八九十'

# ---------- 1. 文本 ----------
def read_docx(p):
    x = zipfile.ZipFile(p).read('word/document.xml').decode()
    out = []
    for para in re.findall(r'<w:p[ >].*?</w:p>', x, flags=re.S):
        t = ''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', para, flags=re.S))
        t = t.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&apos;', "'")
        if t.strip(): out.append(t.strip())
    return out

def to_sentences(paras):
    out = []
    for p in paras:
        p = re.sub(r'\*\*|^#+\s*', '', p).replace('　', ' ').strip().lstrip('■□●◆ ')
        out += [s.strip() for s in re.split(r'(?<=[。！？；])', p) if s.strip()]
    return out

def load_fulltext(src):
    """会议通稿全文，按原文段落保存，供“原文”视图逐段阅读。"""
    F = {}
    for f in glob.glob(os.path.join(src, '当前/数据/99_原有数据包/数据/中央经济工作会议/*.docx')):
        b = os.path.basename(f)
        if b.startswith('~$'): continue
        F[re.search(r'(\d{4})', b).group(1)] = [p.lstrip('■□●◆ ').strip() for p in read_docx(f) if p.strip()]
    return dict(sorted(F.items()))

def load_corpus(src):
    C, G = {}, {}
    for f in glob.glob(os.path.join(src, '当前/数据/99_原有数据包/数据/中央经济工作会议/*.docx')):
        b = os.path.basename(f)
        if b.startswith('~$'): continue
        C[re.search(r'(\d{4})', b).group(1)] = to_sentences(read_docx(f))
    for f in glob.glob(os.path.join(src, '重做_概念史/数据/政府工作报告/*.md')):
        y = os.path.basename(f)[:4]
        G[y] = to_sentences([l for l in open(f, encoding='utf-8').read().split('\n') if l.strip()])
    return {'C': dict(sorted(C.items())), 'G': dict(sorted(G.items()))}

# ---------- 2. 信息观念编码（概念用例编码表 v0 + 早期位阶编码） ----------
def load_usages(src):
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(src, '重做_概念史/编码/概念用例编码表_v0.xlsx'), read_only=True, data_only=True)
    rows = list(wb['用例编码'].iter_rows(values_only=True)); ix = {k: i for i, k in enumerate(rows[0])}
    grp = {}
    for x in rows[1:]:
        if x[ix['V2纳入(Y/N)']] != 'Y': continue
        s = 'C' if x[ix['文本']] == 'CEWC' else 'G'; y = int(x[ix['年份']])
        t = x[ix['所在整句']].lstrip('■□●◆ ').strip()
        g = grp.setdefault((s, y, t, x[ix['节点']]), {'s': s, 'y': y, 'n': x[ix['节点']], 't': t, 'w': [],
             'sense': x[ix['V3义项(预填)']], 'role': x[ix['V5治理角色(预填)']], 'dom': x[ix['V9政策领域(预填)']]})
        if x[ix['匹配词']] not in g['w']: g['w'].append(x[ix['匹配词']])
    U = list(grp.values())
    wb2 = openpyxl.load_workbook(os.path.join(src, '当前/数据/02_处理中间数据/散落表格/中央经济工作会议编码（26012317）.xlsx'), read_only=True, data_only=True)
    rr = list(wb2['工作表1'].iter_rows(values_only=True)); j = {k: i for i, k in enumerate(rr[0])}
    A, meet, themes = [], {}, {}
    for x in rr[1:]:
        if not x[j['年份']]: continue
        y = int(x[j['年份']]); meet[y] = {'meet': x[j['会议时间']], 'pub': str(x[j['通稿时间']])[:10]}
        themes.setdefault(y, x[j['关键主题']])
        if x[j['有关表达']]:
            A.append({'y': y, 'e': str(x[j['有关表达']]).strip('“”"'), 'rank': x[j['治理位阶']], 'emb': x[j['政策嵌入']],
                      'open': x[j['开放编码']], 'sel': x[j['选择性编码']], 'match': None})
    for i, a in enumerate(A):   # 注释挂到对应句子：按片段覆盖率取最佳句，覆盖率≥60%才挂
        fr = [p for p in re.split(r'……|…|”“|“|”|，|。|；|、', a['e']) if len(p) >= 8]
        if not fr: continue
        best, bs = None, 0
        for k, u in enumerate(U):
            if u['s'] == 'C' and u['y'] == a['y']:
                sc = sum(len(f) for f in fr if f in u['t']) / sum(len(f) for f in fr)
                if sc > bs: bs, best = sc, k
        if best is not None and bs >= .6:
            U[best].setdefault('ann', []).append(i); a['match'] = best
    return U, A, meet, themes

# ---------- 3. 重点任务、定调、形势判断、经验总结 ----------
CAT_RULES = [('房地产', r'住房|房地产'), ('三农', r'农业|农村|三农|粮食|乡村|农民|种子|耕地'), ('科技创新', r'科技|创新|新动能|科教|人才'),
    ('生态与双碳', r'生态|环境保护|节能|碳|绿色|资源节约|污染'), ('风险防范', r'风险|债务|攻坚战|金融工作|底线'),
    ('宏观调控', r'宏观调控|宏观政策|财政政策|货币政策|增长速度|稳定增长|物价|通货膨胀|预期目标|增收节支|固定资产投资|宏观经济环境'),
    ('扩大内需', r'内需|消费|国内市场'), ('产业与结构', r'供给侧|三去|产能|降低成本|有效供给|结构|产业|工业|制造业|实体经济|新增长点|发展方式|工交'),
    ('区域与城镇化', r'区域|西部|城镇化|空间格局|城乡融合|地区|协调发展'), ('改革', r'改革|国有企业|体制|市场主体|毫不动摇|反垄断|资本无序|政府职能'),
    ('对外开放', r'开放|外资|出口|外贸|国际|入世'), ('民生与就业', r'民生|就业|社会保障|群众|生活|社会事业|社会政策|公共服务|社会和谐|社会稳定')]

def classify(h):
    for n, p in CAT_RULES:
        if re.search(p, h): return n
    return '其他'

def auto_tasks(text):
    best = []
    for pat in [r'([一二三四五六七八九十]{1,2})是', r'（([一二三四五六七八九十]{1,2})）', r'(?<![\d])([一二三四五六七八九十]{1,2})、']:
        runs, cur = [], []
        for m in re.finditer(pat, text):
            n = m.group(1); k = ORD.index(n[-1]) + 1 + (10 if len(n) > 1 else 0)
            if k == 1:
                if cur: runs.append(cur)
                cur = [m]
            elif cur and k == len(cur) + 1: cur.append(m)
        if cur: runs.append(cur)
        for r in runs:
            if len(r) > len(best): best = r
    return [re.split(r'[。；：]', text[m.end():m.end() + 60])[0][:30] for m in best]

STANCE_OVERRIDE = {  # 通稿未给出明确定性或自动抽取有误的年份，人工核定
    '1994': ('未定性', '未定性', '增收节支', '严格控制信贷规模'),
    '1998': ('积极', '适当', '第三，继续实行积极的财政政策', '实行适当的货币政策'),
    '1999': (None, '未定性', None, '要进一步发挥货币政策的作用')}

def stance(sents, y):
    A = r'(更加积极|积极|稳健|适度从紧|适度宽松|从紧|适当|灵活适度)'
    F = M = Fs = Ms = None
    for s in sents:
        if not re.search(r'实施|实行|继续|坚持|要|保持', s): continue
        if re.search(r'今年|过去|以来|五年|实践证明|一年来', s) and '明年' not in s: continue
        for m in re.finditer(A + r'的财政货币政策', s): F = M = m.group(1); Fs = Ms = s
        for m in re.finditer(A + r'的财政政策和(?:' + A + r'的)?货币政策', s): F = m.group(1); M = m.group(2) or m.group(1); Fs = Ms = s
        if not F and (m := re.search(A + r'的财政政策', s)): F, Fs = m.group(1), s
        if not M and (m := re.search(A + r'的货币政策', s)): M, Ms = m.group(1), s
    if y in STANCE_OVERRIDE:
        f, m_, fk, mk = STANCE_OVERRIDE[y]
        if f: F, Fs = f, next(s for s in sents if fk in s)
        if m_: M, Ms = m_, next(s for s in sents if mk in s)
    return {'f': F, 'm': M, 'fs': Fs, 'ms': Ms}

def diagnosis(ss):
    PW = r'困难|挑战|压力|矛盾|下行|不确定|隐患|不足|偏弱|突出问题|风险|下降|放慢|不旺'
    best, bs = None, 0
    for i, s in enumerate(ss[:int(len(ss) * .6)]):
        if re.search(r'规律性认识|认识和体会|经验', s): continue
        if re.search(r'顶住|面对|有效应对|经受|过去5年|一年来|今年以来|取得|成绩殊', s) and not re.search(r'同时|必须看到|清醒', s): continue
        if not re.search(r'会议指出|会议强调|会议认为|同时|必须看到|清醒|也要看到|但要看到|当前|突出的问题|问题是', s): continue
        k, full = i, s
        while full[-1] in '；：' and k + 1 < len(ss): k += 1; full += ss[k]
        sc = len(re.findall(PW, full)) + (3 if re.search(r'问题是|主要是', full) else 0) + (1 if re.search(r'必须看到|清醒', full) else 0)
        if sc > bs: bs, best = sc, full
    return best if bs >= 2 else None

def lessons(t):
    m = re.search(r'(规律性认识|认识和体会|深刻体会|宝贵经验|几点经验|重要经验)', t)
    if not m: return {'anchor': None, 'items': []}
    rest = t[m.end():].lstrip('：:'); e = re.search(r'会议(指出|强调|认为|要求|确定)', rest)
    seg = rest[:e.start() if e else 800]
    if seg.count('必须') <= 1 and '；' not in seg: seg = seg.split('。')[0]
    items = [p.strip('：: ') for p in re.split(r'；|。|，(?=必须)', seg) if len(p.strip()) > 6][:8]
    k = [i for i in items if re.match(r'(必须|坚持)', i)]
    return {'anchor': m.group(0), 'items': k if len(k) >= 3 else items}

# ---------- 4. 新提法 ----------
def build_terms(corpus):
    T = json.load(open(os.path.join(HERE, 'terms.json'), encoding='utf-8'))
    joinC = {y: ''.join(v) for y, v in corpus['C'].items()}; joinG = {y: ''.join(v) for y, v in corpus['G'].items()}
    out = []
    for typ, ks in T.items():
        for k in ks:
            cy = [int(y) for y in joinC if k in joinC[y]]; gy = [int(y) for y in joinG if k in joinG[y]]
            if not cy: print('  [新提法] 通稿中找不到：', k); continue
            y0 = cy[0]; s = next(s for s in corpus['C'][str(y0)] if k in s); i = s.find(k)
            a, b = max(0, i - 45), min(len(s), i + len(k) + 45)
            gb = [g for g in gy if g <= y0]
            out.append({'k': k, 't': typ, 'y': y0, 'ctx': ('……' if a else '') + s[a:b] + ('……' if b < len(s) else ''),
                        'c': cy, 'g': gy, 'gBefore': gb[-1] if gb else None,
                        'gaps': [(cy[i], cy[i] - cy[i - 1]) for i in range(1, len(cy)) if cy[i] - cy[i - 1] >= 4]})
    return sorted(out, key=lambda x: (x['y'], x['k']))

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--src', required=True); a = ap.parse_args()
    corpus = load_corpus(a.src)
    print('通稿', len(corpus['C']), '份；政府工作报告', len(corpus['G']), '份')
    U, A, meet, themes = load_usages(a.src)
    curated = json.load(open(os.path.join(HERE, 'tasks_curated.json'), encoding='utf-8'))
    tasks, st, diag, rules, quotes = {}, {}, {}, {}, {}
    for y, ss in corpus['C'].items():
        t = ''.join(ss)
        heads = curated.get(y) or auto_tasks(t)
        if y not in curated: print(f'  [任务] {y} 为自动切分，请核对后写入 tasks_curated.json：', heads)
        tasks[y] = [{'r': i + 1, 'h': h, 'cat': classify(h)} for i, h in enumerate(heads)]
        st[y] = stance(ss, y); diag[y] = diagnosis(ss); rules[y] = lessons(t)
        prev = ''.join(''.join(corpus['C'][k]) for k in corpus['C'] if k < y)
        qs = []
        for q in re.findall(r'“([^”]{2,16})”', t):
            if re.search(r'[，。；]', q) or any(x['q'] == q for x in qs): continue
            py = [k for k in corpus['C'] if k < y and q in ''.join(corpus['C'][k])]
            qs.append({'q': q, 'prev': py[-1] if py else None})
        quotes[y] = qs
    site = {'usages': U, 'ann': A, 'meet': meet, 'themes': themes, 'tasks': tasks, 'stance': st,
            'diag': diag, 'rules': rules, 'quotes': quotes, 'terms': build_terms(corpus),
            'milestones': json.load(open(os.path.join(HERE, 'milestones.json'), encoding='utf-8'))}
    os.makedirs(OUT, exist_ok=True)
    json.dump(corpus, open(os.path.join(OUT, 'corpus.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    json.dump(site, open(os.path.join(OUT, 'site.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    json.dump(load_fulltext(a.src), open(os.path.join(OUT, 'fulltext.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    print('概念句', len(U), '；注释', len(A), '（挂靠', sum(1 for x in A if x['match'] is not None), '）；任务',
          sum(len(v) for v in tasks.values()), '；新提法', len(site['terms']))
    print('任务领域分布', Counter(t['cat'] for v in tasks.values() for t in v).most_common())

if __name__ == '__main__':
    main()
