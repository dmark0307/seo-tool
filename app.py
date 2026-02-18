import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정 및 디자인 최소화 적용
st.set_page_config(page_title="SEO NLU", layout="wide")

# 인터페이스 최소화를 위한 강력한 CSS 주입
st.markdown("""
    <style>
    /* 사이드바 너비 고정 및 여백 제거 */
    [data-testid="stSidebar"] { min-width: 280px; max-width: 280px; }
    [data-testid="stSidebarContent"] { padding-top: 1rem; }
    
    /* 위젯 간 간격 극한 축소 */
    [data-testid="stElementContainer"] { margin-bottom: -22px !important; }
    
    /* 파일 업로드 박스 높이 축소 및 안내문구 숨기기 */
    [data-testid="stFileUploader"] section { padding: 0px 10px !important; min-height: 70px !important; }
    [data-testid="stFileUploader"] label { margin-bottom: -10px; font-size: 0.8rem; }
    div[data-testid="stFileUploader"] section > div { display: none; } /* "Drag and drop" 문구 숨기기 */
    
    /* 입력창 라벨 크기 조절 */
    .stTextInput label, .stNumberInput label { font-size: 0.85rem !important; }
    
    /* 본문 상단 여백 축소 */
    .block-container { padding-top: 1rem !important; }
    </style>
    """, unsafe_allow_html=True)

class SEOManager:
    def __init__(self, df, user_exclude_list):
        self.df = df
        self.exclude_brands = ['매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', '희창유업', '담터', '연세유업', '매일유업'] + user_exclude_list
        self.sub_splits = sorted(['자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', '업소용', '대용량', '멸균', '파우치', '추억', '간식', '재료'], key=len, reverse=True)

    def split_base_terms(self, text):
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        pattern = f"({'|'.join(self.sub_splits)})"
        raw_words = text.split()
        terms = []
        for word in raw_words:
            if word in self.exclude_brands or any(char.isdigit() for char in word): continue
            parts = re.split(pattern, word)
            for p in parts:
                p = p.strip()
                if not p or p in self.exclude_brands: continue
                if len(p) > 1 or p in self.sub_splits: terms.append(p)
        return terms

    def extract_stats_data(self, stats_df, target_product_code):
        try:
            code_col = [c for c in stats_df.columns if any(x in c for x in ['번호', 'ID', '코드'])][0]
            kw_col = [c for c in stats_df.columns if '키워드' in c][0]
            name_col = [c for c in stats_df.columns if '상품명' in c][0]
            filtered_df = stats_df[stats_df[code_col].astype(str) == str(target_product_code)]
            if filtered_df.empty: return [], ""
            existing_name = str(filtered_df[name_col].iloc[0])
            raw_keywords = filtered_df[kw_col].dropna().unique().tolist()
            extracted = []
            for rk in raw_keywords:
                if rk != '-': extracted.extend(self.split_base_terms(rk))
            return list(dict.fromkeys(extracted))[:5], existing_name
        except: return [], ""

    def reorder_for_readability(self, word_count_pairs):
        identity, form, usage, desc = ['전지', '분유', '우유', '탈지'], ['분말', '가루', '스틱', '액상'], ['자판기', '업소용', '대용량', '식자재'], ['진한', '고소한', '맛있는', '추억']
        def get_priority(pair):
            word = pair[0]
            if any(core in word for core in identity): return 1
            if any(core in word for core in form): return 2
            if any(core in word for core in usage): return 3
            if any(core in word for core in desc): return 4
            return 5
        return sorted(word_count_pairs, key=lambda x: get_priority(x))

    def run_analysis(self, stats_keywords, conversion_input, add_input, total_target_count):
        conv_keys = stats_keywords + self.split_base_terms(conversion_input)
        add_keys = self.split_base_terms(add_input)
        fixed_keywords = []
        for k in (conv_keys + add_keys):
            if k not in fixed_keywords: fixed_keywords.append(k)
        
        name_terms = []
        for name in self.df['상품명']: name_terms.extend(self.split_base_terms(name))
        name_freq = Counter(name_terms).most_common(50)
        auto_candidates = [w for w, c in name_freq if w not in fixed_keywords]
        remain_count = max(0, total_target_count - len(fixed_keywords))
        selected_auto = auto_candidates[:remain_count]
        readable_auto_pairs = self.reorder_for_readability([(w, Counter(name_terms)[w]) for w in selected_auto])
        
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)
        spec_keywords = set()
        for s, _ in spec_counts: spec_keywords.update(self.split_base_terms(s))
        title_keywords = set(fixed_keywords + [p[0] for p in readable_auto_pairs])

        tag_raw_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-': tag_raw_list.extend([t.strip() for t in str(tags).split(',') if t.strip()])
        tag_freq = Counter(tag_raw_list).most_common(300)
        candidates = []
        for t_raw, c in tag_freq:
            if any(brand in t_raw for brand in self.exclude_brands) or any(char.isdigit() for char in t_raw): continue
            t_subterms = self.split_base_terms(t_raw)
            if not t_subterms or any(sub in title_keywords or sub in spec_keywords for sub in t_subterms): continue
            candidates.append((t_raw, c))

        final_tags, selected_subterms = [], set()
        for i, (t_raw, c) in enumerate(candidates):
            if len(final_tags) >= 10: break
            if any(t_raw in other_t and len(t_raw) < len(other_t) for other_t, _ in candidates): continue
            prefix = t_raw[:3] if len(t_raw) > 3 else t_raw[:2]
            if any(prefix in ex_t or ex_t[:3] in t_raw for ex_t, _ in final_tags): continue
            t_subterms = self.split_base_terms(t_raw)
            if any(sub in selected_subterms for sub in t_subterms): continue
            final_tags.append((t_raw, c)); selected_subterms.update(t_subterms)

        return fixed_keywords, readable_auto_pairs, spec_counts, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

def calculate_seo_metrics(text):
    c_len = len(text)
    try: b_len = len(text.encode('euc-kr'))
    except: b_len = len(text.encode('utf-8'))
    return c_len, b_len

# --- 최적화 사이드바 ---
with st.sidebar:
    st.markdown("### 🛠️ **SEO 설정**")
    
    # 1. 데이터 소스 (압축)
    uploaded_file = st.file_uploader("상품(CSV)", type=["csv"], help="필수 업로드")
    stats_file = st.file_uploader("통계(XL/CSV)", type=["csv", "xlsx"], help="판매분석 파일")
    target_code = st.text_input("🎯 코드", placeholder="상품코드")

    # 2. 전략 설정 (압축)
    conversion_input = st.text_input("➕ 키워드", placeholder="추가 구매전환 단어")
    add_input = st.text_input("📌 고정", placeholder="고정 배치 키워드")
    total_kw_count = st.number_input("🔢 목표", min_value=5, max_value=25, value=11)

# --- 메인 실행부 ---
if uploaded_file:
    try:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df, [])
    stats_kws, old_name = [], ""
    
    if stats_file and target_code:
        try:
            stats_file.seek(0)
            stats_df = pd.read_csv(stats_file, encoding='cp949') if stats_file.name.endswith('.csv') else pd.read_excel(stats_file, engine='openpyxl')
            stats_kws, old_name = manager.extract_stats_data(stats_df, target_code)
        except: pass

    fixed, auto, specs, tags = manager.run_analysis(stats_kws, conversion_input, add_input, total_kw_count)

    # 1. 전략적 상품명 조합 (디자인 유지)
    st.header("🏷️ 1. 전략적 상품명 조합")
    if old_name: st.info(f"📝 **기존:** {old_name}")
    full_title = " ".join(fixed + [p[0] for p in auto])
    st.code(full_title, language=None)
    c_l, b_l = calculate_seo_metrics(full_title)
    st.markdown(f"**{c_l}자 / {b_l} Byte / {len(fixed)+len(auto)}개 키워드**")

    st.markdown("---")

    # 2 & 3. 속성 및 태그 (이미지 77c3cc 완벽 재현)
    st.header("⚙️ 2. 필터 속성 & 🔍 3. 확장 태그")
    col_l, col_r = st.columns(2)
    with col_l:
        for s_name, _ in specs: st.button(s_name, use_container_width=True, key=f"btn_{s_name}")
    with col_r:
        st.success(", ".join([f"#{t[0]}" for t in tags]))
else:
    st.info("좌측에서 상품 데이터를 업로드하세요.")
