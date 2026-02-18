import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정 및 디자인 극한 최적화
st.set_page_config(page_title="SEO NLU", layout="wide")

# 사이드바 스크롤 제거 및 위젯 간격 최소화를 위한 강력한 CSS
st.markdown("""
    <style>
    /* 사이드바 너비 고정 및 여백 극한 축소 */
    [data-testid="stSidebar"] { min-width: 260px; max-width: 260px; }
    [data-testid="stSidebarContent"] { padding-top: 0.5rem; }
    [data-testid="stElementContainer"] { margin-bottom: -24px !important; } /* 위젯 간격 최소화 */
    
    /* 파일 업로드 박스 최소화 및 불필요한 텍스트 숨기기 */
    [data-testid="stFileUploader"] section { padding: 0px 5px !important; min-height: 60px !important; border: 1px solid #ddd; }
    [data-testid="stFileUploader"] label { font-size: 0.8rem; margin-bottom: -15px; }
    [data-testid="stFileUploader"] section > div { display: none; } /* "Drag and drop" 문구 삭제 */
    
    /* 입력창 및 라벨 폰트 축소 */
    .stTextInput label, .stNumberInput label { font-size: 0.8rem !important; }
    .stTextInput input, .stNumberInput input { height: 32px !important; font-size: 0.85rem !important; }
    
    /* 본문 상단 여백 축소 */
    .block-container { padding-top: 1rem !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 네이버 쇼핑 SEO 통합 최적화 매니저")
st.markdown("---")

class SEOManager:
    def __init__(self, df, user_exclude_list):
        self.df = df
        self.exclude_brands = ['매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', '희창유업', '담터', '연세유업', '매일유업'] + user_exclude_list
        self.sub_splits = sorted(['자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', '업소용', '대용량', '멸균', '파우치', '추억', '간식', '재료'], key=len, reverse=True)

    def split_base_terms(self, text, is_manual=False):
        """NLU 규칙 분리 (is_manual=True 시 사용자가 엔터 친 키워드 100% 보존)"""
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        raw_words = text.split()
        terms = []
        pattern = f"({'|'.join(self.sub_splits)})"
        for word in raw_words:
            if word in self.exclude_brands: continue
            if not is_manual and any(char.isdigit() for char in word): continue
            parts = re.split(pattern, word)
            for p in parts:
                p = p.strip()
                if not p or p in self.exclude_brands: continue
                if is_manual or len(p) > 1 or p in self.sub_splits: terms.append(p)
        return terms

    def extract_stats_data(self, stats_df, target_product_code):
        """통계 파일에서 기존 상품명과 결제 키워드 추출"""
        try:
            code_col = [c for c in stats_df.columns if any(x in c for x in ['번호', 'ID', '코드'])][0]
            kw_col = [c for c in stats_df.columns if '키워드' in c][0]
            name_col = [c for c in stats_df.columns if '상품명' in c][0]
            filtered = stats_df[stats_df[code_col].astype(str) == str(target_product_code)]
            if filtered.empty: return [], ""
            old_name = str(filtered[name_col].iloc[0])
            raw_kws = filtered[kw_col].dropna().unique().tolist()
            extracted = []
            for rk in raw_kws:
                if rk != '-': extracted.extend(self.split_base_terms(rk))
            return list(dict.fromkeys(extracted))[:5], old_name
        except: return [], ""

    def reorder_for_readability(self, pairs):
        identity, form, usage = ['전지', '분유', '우유'], ['분말', '가루', '스틱'], ['자판기', '업소용']
        def get_priority(pair):
            w = pair[0]
            if any(c in w for c in identity): return 1
            if any(c in w for c in form): return 2
            if any(c in w for c in usage): return 3
            return 4
        return sorted(pairs, key=lambda x: get_priority(x))

    def run_analysis(self, stats_kws, conv_input, add_input, target_count):
        # 수동 입력 키워드 분해
        manual_conv = self.split_base_terms(conv_input, is_manual=True)
        manual_add = self.split_base_terms(add_input, is_manual=True)
        
        # [요청사항] 배치 순서 적용: 통계 -> 고정(add) -> 전환추가(conv)
        fixed_keywords = []
        for k in (stats_kws + manual_add + manual_conv):
            if k not in fixed_keywords: fixed_keywords.append(k)
        
        # 자동 추출 키워드
        name_terms = []
        for n in self.df['상품명']: name_terms.extend(self.split_base_terms(n))
        name_freq = Counter(name_terms).most_common(100)
        auto_cands = [w for w, c in name_freq if w not in fixed_keywords]
        selected_auto = auto_cands[:max(0, target_count - len(fixed_keywords))]
        
        # 섹션 2: 속성
        spec_list = []
        for s in self.df['스펙'].dropna():
            parts = [p.strip() for p in str(s).split('|')]
            spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        specs = Counter(spec_list).most_common(8)
        spec_kws = set([s[0] for s in specs])
        
        # 섹션 3: 태그 (확장성 로직 유지)
        tag_raw = []
        for t in self.df['검색인식태그'].dropna():
            tag_raw.extend([i.strip() for i in str(t).split(',') if i.strip()])
        tag_freq = Counter(tag_raw).most_common(300)
        title_set = set(fixed_keywords + selected_auto)
        final_tags, used_sub = [], set()
        for t_raw, c in tag_freq:
            if len(final_tags) >= 10: break
            if any(b in t_raw for b in self.exclude_brands) or any(d.isdigit() for d in t_raw): continue
            t_sub = self.split_base_terms(t_raw)
            if not t_sub or any(s in title_set or s in spec_kws or s in used_sub for s in t_sub): continue
            final_tags.append((t_raw, c)); used_sub.update(t_sub)

        return fixed_keywords, [(w, Counter(name_terms)[w]) for w in selected_auto], specs, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

def calc_metrics(text):
    c_l = len(text)
    try: b_l = len(text.encode('euc-kr'))
    except: b_l = len(text.encode('utf-8'))
    return c_l, b_l

# --- 최적화 사이드바 구성 ---
with st.sidebar:
    st.markdown("### 🛠️ **SEO 설정**")
    # 업로드 박스 최소화
    main_file = st.file_uploader("상품(CSV)", type=["csv"], help="분석용 데이터")
    stats_file = st.file_uploader("통계(XL/CSV)", type=["csv", "xlsx"], help="판매분석 파일")
    target_id = st.text_input("🎯 상품코드", placeholder="코드 입력")
    # 전략 위젯 압축
    conv_in = st.text_input("➕ 추가", placeholder="전환 키워드")
    add_in = st.text_input("📌 고정", placeholder="고정 배치")
    total_kw = st.number_input("🔢 목표", min_value=5, value=11)

# --- 메인 로직 ---
if main_file:
    try:
        main_file.seek(0)
        df = pd.read_csv(main_file, encoding='cp949')
    except:
        main_file.seek(0)
        df = pd.read_csv(main_file, encoding='utf-8-sig')

    manager = SEOManager(df, [])
    stats_kws, old_name = [], ""
    
    if stats_file and target_id:
        try:
            stats_file.seek(0)
            s_df = pd.read_csv(stats_file, encoding='cp949') if stats_file.name.endswith('.csv') else pd.read_excel(stats_file, engine='openpyxl')
            stats_kws, old_name = manager.extract_stats_data(s_df, target_id)
            if stats_kws: st.sidebar.success("✔️ 매칭 성공")
        except: pass

    fixed, auto, specs, tags = manager.run_analysis(stats_kws, conv_in, add_in, total_kw)

    # 섹션 1: 상품명
    st.header("🏷️ 1. 전략적 상품명 조합")
    if old_name: st.info(f"📝 **기존:** {old_name}")
    full_title = " ".join(fixed + [p[0] for p in auto])
    st.code(full_title, language=None)
    cl, bl = calc_metrics(full_title)
    st.markdown(f"**{cl}자 / {bl} Byte / {len(fixed)+len(auto)}개 키워드**")

    st.markdown("---")

    # 섹션 2 & 3: 속성 및 태그 (이미지 77c3cc 완벽 유지)
    st.header("⚙️ 2. 필터 속성 & 🔍 3. 확장 태그")
    l_col, r_col = st.columns(2)
    with l_col:
        for sn, _ in specs: st.button(sn, use_container_width=True, key=f"btn_{sn}")
    with r_col:
        tag_str = ", ".join([f"#{t[0]}" for t in tags])
        st.success(tag_str)
else:
    st.info("좌측 사이드바에서 상품 데이터를 먼저 업로드해 주세요.")
