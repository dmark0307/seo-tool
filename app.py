import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정 및 디자인 극한 최적화
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")

# 사이드바 스크롤 방지 및 인터페이스 압축 CSS
st.markdown("""
    <style>
    [data-testid="stSidebar"] { min-width: 300px; max-width: 300px; }
    [data-testid="stSidebarContent"] { padding-top: 1rem; }
    [data-testid="stElementContainer"] { margin-bottom: -22px !important; }
    
    /* 파일 업로드 박스 디자인 최소화 */
    [data-testid="stFileUploader"] section { padding: 0px 10px !important; min-height: 75px !important; }
    [data-testid="stFileUploader"] label { font-size: 0.8rem; margin-bottom: -15px; }
    [data-testid="stFileUploader"] section > div { display: none; } /* "Drag and drop" 문구 제거 */
    
    .stTextInput label, .stNumberInput label { font-size: 0.8rem !important; }
    .block-container { padding-top: 1.5rem !important; }
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
        """NLU 규칙 분리 (수동 입력 시 보존 로직 강화)"""
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
        """통계 데이터에서 메인 키워드, 결제 키워드, 기존 상품명 추출"""
        try:
            code_col = [c for c in stats_df.columns if any(x in c for x in ['번호', 'ID', '코드'])][0]
            kw_col = [c for c in stats_df.columns if '키워드' in c][0]
            name_col = [c for c in stats_df.columns if '상품명' in c][0]
            
            # 1. 전체 데이터에서 검색 빈도가 높은 '메인 키워드' 추출
            all_kws = stats_df[kw_col].dropna().apply(lambda x: self.split_base_terms(x, is_manual=True)).explode().dropna()
            main_keywords = [item[0] for item in Counter(all_kws).most_common(10) if item[0] not in self.exclude_brands]

            # 2. 특정 상품 매칭 데이터 추출
            filtered_df = stats_df[stats_df[code_col].astype(str) == str(target_product_code)]
            if filtered_df.empty: return [], [], ""
            
            existing_name = str(filtered_df[name_col].iloc[0])
            raw_keywords = filtered_df[kw_col].dropna().unique().tolist()
            extracted = []
            for rk in raw_keywords:
                if rk != '-': extracted.extend(self.split_base_terms(rk, is_manual=True))
            
            return main_keywords, list(dict.fromkeys(extracted))[:5], existing_name
        except: return [], [], ""

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
        # 입력값 분해
        manual_conv = self.split_base_terms(conversion_input, is_manual=True)
        manual_add = self.split_base_terms(add_input, is_manual=True)
        
        # [요청사항] 배치 순서 적용: [통계] -> [고정] -> [추가전환]
        fixed_keywords = []
        for k in (stats_keywords + manual_add + manual_conv):
            if k not in fixed_keywords: fixed_keywords.append(k)
        
        name_terms = []
        for name in self.df['상품명']: name_terms.extend(self.split_base_terms(name))
        name_freq = Counter(name_terms).most_common(50)
        auto_candidates = [w for w, c in name_freq if w not in fixed_keywords]
        
        selected_auto = auto_candidates[:max(0, total_target_count - len(fixed_keywords))]
        readable_auto_pairs = self.reorder_for_readability([(w, Counter(name_terms)[w]) for w in selected_auto])
        
        # 2번 섹션: 속성 분석 (로직 유지)
        spec_list = []
        for spec in self.df['스펙'].dropna():
            parts = [p.strip() for p in str(spec).split('|')]
            spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        specs = Counter(spec_list).most_common(8)
        spec_kws = set([s[0] for s in specs])

        # 3번 섹션: 태그 분석 (로직 유지)
        tag_raw = []
        for t in self.df['검색인식태그'].dropna():
            tag_raw.extend([i.strip() for i in str(t).split(',') if i.strip()])
        tag_freq = Counter(tag_raw).most_common(300)
        title_set = set(fixed_keywords + [p[0] for p in readable_auto_pairs])
        final_tags, used_sub = [], set()
        for t_raw, c in tag_freq:
            if len(final_tags) >= 10: break
            if any(b in t_raw for b in self.exclude_brands) or any(d.isdigit() for d in t_raw): continue
            t_sub = self.split_base_terms(t_raw)
            if not t_sub or any(s in title_set or s in spec_kws or s in used_sub for s in t_sub): continue
            final_tags.append((t_raw, c)); used_sub.update(t_sub)

        return fixed_keywords, readable_auto_pairs, specs, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

def calculate_seo_metrics(text):
    c_len = len(text)
    try: b_len = len(text.encode('euc-kr'))
    except: b_len = len(text.encode('utf-8'))
    return c_len, b_len

# --- 사이드바 UI 최적화 구성 ---
with st.sidebar:
    st.markdown("### 🛠️ **SEO 엔진 설정**")
    with st.expander("📁 데이터 소스", expanded=True):
        uploaded_file = st.file_uploader("상품(CSV)", type=["csv"])
        stats_file = st.file_uploader("통계(XL/CSV)", type=["csv", "xlsx"])
        target_code = st.text_input("🎯 상품코드", placeholder="코드 입력")

    with st.expander("🎯 전략 설정", expanded=True):
        add_in = st.text_input("📌 고정 배치", placeholder="예: 무료배송")
        conv_in = st.text_input("➕ 추가 전환", placeholder="예: 맛있는 우유")
        total_kw = st.number_input("🔢 목표 수", min_value=5, value=11)

if uploaded_file:
    try:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df, [])
    main_kws, stats_kws, old_name = [], [], ""
    
    if stats_file and target_code:
        try:
            stats_file.seek(0)
            stats_df = pd.read_csv(stats_file, encoding='cp949') if stats_file.name.endswith('.csv') else pd.read_excel(stats_file, engine='openpyxl')
            main_kws, stats_kws, old_name = manager.extract_stats_data(stats_df, target_code)
            if stats_kws: st.sidebar.success("✔️ 통계 매칭 완료")
        except: st.sidebar.error("통계 분석 오류")

    fixed, auto, specs, tags = manager.run_analysis(stats_kws, conv_in, add_in, total_kw)

    # 1. 전략적 상품명 조합
    st.header("🏷️ 1. 전략적 상품명 조합")
    col1, col2 = st.columns([2, 1])
    with col1:
        if old_name: st.info(f"📝 **기존 상품명:** {old_name}")
        if main_kws: st.warning(f"🔥 **통계 기반 메인 키워드(추천):** {', '.join(main_kws)}")
            
        st.subheader("✅ 완성된 상품명")
        full_title = " ".join(fixed + [p[0] for p in auto])
        st.code(full_title, language=None)
        cl, bl = calculate_seo_metrics(full_title)
        st.markdown(f"**{cl}자 / {bl} Byte / {len(fixed)+len(auto)}개 키워드**")
        if stats_kws: st.success(f"📊 **반영된 결제 키워드:** {', '.join(stats_kws)}")

    with col2:
        st.subheader("📊 자동 추천 빈도")
        st.table(pd.DataFrame(auto, columns=['단어', '빈도']).assign(No=range(1, len(auto)+1)).set_index('No'))

    st.markdown("---")
    # 2 & 3번 섹션 (로직 및 출력 방식 철저히 유지)
    st.header("⚙️ 2. 필터 속성 & 🔍 3. 확장 태그")
    l_col, r_col = st.columns(2)
    with l_col:
        for s_name, _ in specs: st.button(s_name, use_container_width=True, key=f"at_{s_name}")
    with r_col:
        st.success(", ".join([f"#{t[0]}" for t in tags]))
else:
    st.info("좌측 메뉴에서 상품 데이터를 업로드해주세요.")
