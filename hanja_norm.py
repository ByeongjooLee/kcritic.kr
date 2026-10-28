# -*- coding: utf-8 -*-
"""한자 → 한글 표기, 대학명 「OO대」 통일 (2026-10-28, 연구자 결정)

공개 데이터(genealogy-library.json · research-public.json · academic-network-public.json)의 논문 제목·인물 이름·대학명을
한글로 보이고, 대학명은 「학교」를 뗀 「OO대」로 통일한다. 원표기는 *_raw 필드에 그대로 남긴다(그전 데이터 유지).

- h2k(text): 한자를 한글 음으로. `hanja` 패키지(두음법칙은 낱말 첫머리에만 적용)에 두 가지 보정을 얹는다.
  ① 낱말 가운데서도 두음법칙이 필요한 말(女性·歷史·理論·浪漫 …)은 MID_WORDS 사전으로 경계를 끊는다.
     年代(1930년대)·論(문학론)·道(전라도)처럼 가운데서는 두음법칙이 없는 말은 사전에 넣지 않는다.
  ② 성씨 金은 「김」(패키지 기본값은 「금」). 金融·金屬처럼 낱말인 경우만 「금」.
  「이상(李箱)」처럼 한글 뒤 괄호의 한자가 같은 음이면 괄호를 뗀다. 호환 한자(U+F900–)는 정규 한자로 바꾼다.
- uni_norm(raw): 대학 표기 → 「OO대」. 한자 교명 → 한글, 「대학원·학과·전공」 제거, 캠퍼스는 유지(「고려대 세종캠퍼스」),
  별칭 통일(경상국립대=경상대, 강원대(강릉)=강릉원주대, 경원대=가천대 …), 「대학교」→「대」, 「여자대」→「여대」.
  이미 「OO대」인 값은 그대로(멱등).
"""
import re, unicodedata
import hanja

HANJA_RE = re.compile(r'[一-鿿㐀-䶿豈-﫿]')
HANJA_RUN = re.compile(r'[一-鿿㐀-䶿豈-﫿]+')

# 낱말 가운데서도 두음법칙이 적용되는 말(앞 글자가 ㄹ·ㄴ 초성). 긴 것부터 맞춘다.
MID_WORDS = {
    '女性': '여성', '女子': '여자', '女流': '여류', '女人': '여인', '女學生': '여학생', '歷史': '역사', '理論': '이론', '理解': '이해',
    '理念': '이념', '理想': '이상', '理性': '이성', '倫理': '윤리', '論理': '논리', '論爭': '논쟁', '論議': '논의', '勞動': '노동',
    '老人': '노인', '浪漫': '낭만', '戀愛': '연애', '戀情': '연정', '旅行': '여행', '旅愁': '여수', '離散': '이산', '離別': '이별',
    '良心': '양심', '良識': '양식', '力量': '역량', '流行': '유행', '流動': '유동', '流浪': '유랑', '留學': '유학', '利用': '이용',
    '隣人': '이인', '念願': '염원', '來日': '내일', '樂園': '낙원', '落葉': '낙엽', '陸史': '육사', '連帶': '연대', '連載': '연재',
    '靈魂': '영혼', '禮儀': '예의', '禮節': '예절', '料理': '요리', '類型': '유형', '輪廻': '윤회', '路線': '노선', '勞使': '노사',
    '龍飛': '용비', '李箱': '이상', '李光洙': '이광수', '林和': '임화', '梨花': '이화', '六堂': '육당',
}
MID_WORDS.update({'類形': '유형', '樂劇': '악극', '音樂': '음악',
                  # 모음·ㄴ 받침 뒤의 律·列·烈·率 은 「율·열」 (패키지는 률·렬로 읽는다)
                  '韻律': '운율', '旋律': '선율', '規律': '규율', '自律': '자율', '比率': '비율', '效率': '효율', '利率': '이율',
                  '分裂': '분열', '羅列': '나열', '陳列': '진열', '序列': '서열', '先烈': '선열', '百分率': '백분율'})
MID_KEYS = sorted(MID_WORDS, key=len, reverse=True)
GEUM_WORDS = ('融', '錢', '屬', '石', '銀', '剛', '器', '額', '利', '庫', '科', '塊', '鑛', '品', '曜')   # 金 뒤에 오면 「금」
# 세 글자 인명(성 + 두 글자 이름): 이름 첫 글자에도 두음법칙 (韓龍雲 한용운, 張龍鶴 장용학, 金玲美 김영미). 제목 안에서는 끝 글자가
# 낱말 꼬리(道·論·史 …)가 아닐 때만 인명으로 본다 (全羅道 전라도는 그대로).
SURNAMES = set('金李朴崔鄭姜趙尹張林韓吳申徐權黃安宋柳全洪高文梁孫白曺許南沈劉盧河田郭成車周禹具羅辛閔兪池陳嚴元蔡千方楊孔玄康咸卞廉魯呂秋都石蘇薛宣馬吉延表明奇殷片龍王班玉陸印魚牟庾桂太卓菊')
SUFFIX = set('道論史學派院社性的化觀主期層文詩說劇集誌報館園堂洞里山江川國家族會黨軍法校科部局線路市郡村界')

def _nfkc_hanja(s):
    return ''.join(unicodedata.normalize('NFKC', c) if '豈' <= c <= '﫿' else c for c in s)

def _word(buf, name):
    if (name and 2 <= len(buf) <= 4 or len(buf) == 3 and buf[2] not in SUFFIX) and buf[0] in SURNAMES:
        sur = '김' if buf[0] == '金' else hanja.translate(buf[0], 'substitution')
        return sur + hanja.translate(buf[1:], 'substitution')
    k = hanja.translate(buf, 'substitution')
    if buf[0] == '金' and len(buf) >= 2 and buf[1] not in GEUM_WORDS: k = '김' + k[1:]   # 성씨 金
    return k

def _run(run, name=False):
    """한자 연속 구간 하나를 한글로."""
    out, buf, i = [], '', 0
    def flush():
        nonlocal buf
        if buf: out.append(_word(buf, name)); buf = ''
    while i < len(run):
        hit = next((w for w in MID_KEYS if run.startswith(w, i)), None)
        if hit: flush(); out.append(MID_WORDS[hit]); i += len(hit); continue
        buf += run[i]; i += 1
    flush()
    return ''.join(out)

def h2k(text, name=False):
    """name=True 는 인물 이름 칸(두 글자 이상이면 모두 성+이름으로 읽는다)."""
    s = _nfkc_hanja(str(text or ''))
    if not HANJA_RE.search(s): return s
    if name: return HANJA_RUN.sub(lambda m: _run(m.group(0), True), s)
    # 「一九三〇年代」→「1930년대」: 年 앞의 한자 숫자는 아라비아 숫자로, 숫자 뒤 年(代)는 두음법칙 없이 「년」
    s = re.sub(r'[一二三四五六七八九〇○零]{2,}(?=\s*年)', lambda m: ''.join(str('〇○零一二三四五六七八九'.index(c) % 10) if c in '〇○零' else str('一二三四五六七八九'.index(c) + 1) for c in m.group(0)), s)
    s = re.sub(r'(\d)\s*年代', r'\1년대', s); s = re.sub(r'(\d)\s*年', r'\1년', s)
    s = HANJA_RUN.sub(lambda m: _run(m.group(0)), s)
    # 「이상(李箱)」→「이상」: 괄호 안 한자가 앞 한글과 같은 음이면 괄호를 뗀다 (원문에서 한자가 괄호 안에 있던 자리)
    s = re.sub(r'([가-힣]+)\(([가-힣\s]+)\)', lambda m: m.group(1) if m.group(2).replace(' ', '') == m.group(1) else m.group(0), s)
    return s

# ── 대학명
UNI_HANJA = [('韓國學中央硏究院', '한국학중앙연구원'), ('韓國學大學院', '')]
ALIAS = {'경상국립대학교': '경상대학교', '국립창원대학교': '창원대학교', '국립공주대학교': '공주대학교', '국립경국대학교': '경국대학교',
         '강원대학교(강릉)': '강릉원주대학교', '강릉대학교': '강릉원주대학교', '경원대학교': '가천대학교', '서울大': '서울대학교',
         '경경희대학교': '경희대학교'}   # 통합목록의 OCR 오류 「慶경희대학교」

def uni_norm(value):
    s = str(value or '').strip()
    for h, k in UNI_HANJA: s = s.replace(h, k)
    s = h2k(s).replace('녀자', '여자')
    s = re.sub(r'^국립\s*', '', s).strip()
    s = ALIAS.get(s, s)
    campus = re.search(r'(?:[가-힣A-Za-z]+캠퍼스|\((?:강릉|원주|세종|천안|서울|용인|에리카|ERICA)[^)]*\))', s)
    m = re.match(r'^.*?(?:대학교|사관학교|과학기술원|중앙연구원|연구원)', s)
    if m:
        school = ALIAS.get(m.group(0), m.group(0))
        s = school + (' ' + campus.group(0) if campus and campus.group(0) not in school else '')
    else:
        s = re.sub(r'\s*(?:일반|전문|특수|교육)?대학원.*$', '', s).strip()
    return s.replace('여자대학교', '여대').replace('대학교', '대')

if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    for a in sys.argv[1:]: print(a, '→', h2k(a), '|', uni_norm(a))
