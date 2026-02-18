import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정 (최상단 고정)
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 매니저")
st.markdown("---")

class SEOManager:
    def __init__(self, df, user_exclude_list):
        self.df = df
        self.exclude_brands = [
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ] + user_exclude_list
        self.sub_splits = sorted(['자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', '업소용', '대용량', '멸균', '파우치', '추억', '간식', '재료'], key=len, reverse=True)

    def split_base_terms(self, text):
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        raw_words = text.split()
        terms = []
        pattern = f"({'|'.join(self.sub_splits)})"
        for word in raw_words:
            if word in self.exclude_brands or any(char.isdigit() for char in word): continue
            parts = re.split(pattern, word)
            for p in parts:
                p = p.strip()
                if not p or p in self.exclude_brands: continue
                if len(p) > 1 or p in self.sub_splits: terms.append(p)
        return terms

    def extract_stats_keywords(self, stats_df, target_product_code):
        try:
            code_col = [c for c in stats_df.columns if any(x in c for x in ['번호', 'ID', '코드'])][0]
            kw_col = [c for c in stats_df.columns if '키워드' in c][0]
            filtered_df = stats_df[stats_df[code_col].astype(str) == str(target_product_code)]
            raw_keywords = filtered_df[kw_col].dropna().unique().tolist()
            extracted = []
            for rk in raw_keywords:
                if rk != '-': extracted.extend(self.split_base_terms(rk))
            return list(dict.fromkeys(extracted))[:5]
        except: return []

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
        
        spec_list = []
        for spec in self.df['스펙'].dropna():
            parts = [p.strip() for p in str(spec).split('|')]
            spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)
        spec_keywords = set()
        for s, _ in spec_counts: spec_keywords.update(self.split_base_terms(s))

        title_keywords = set(fixed_keywords + selected_auto)
        tag_raw_list = []
        for tags in self.df['검색인식태그'].dropna():
            tag_raw_list.extend([t.strip() for t in str(tags).split(',') if t.strip()])
        tag_freq = Counter(tag_raw_list).most_common(300)
        candidates = []
        for t_raw, c in tag_freq:
            if any(brand in t_raw for brand in self.exclude_brands): continue
            if any(char.isdigit() for char in t_raw): continue
            t_subterms = self.split_base_terms(t_raw)
            if not t_subterms or any(sub in title_keywords or sub in spec_keywords for sub in t_subterms): continue
            candidates.append((t_raw, c))

        final_tags, selected_subterms = [], set()
        for i, (t_raw, c) in enumerate(candidates):
            if len(final_tags) >= 10: break
            if any(t_raw in other_t and len(t_raw) < len(other_t) for other_t, _ in candidates): continue
            prefix = t_raw[:3] if len(t_raw) > 3 else t_raw[:2]
            if any(prefix in ex_t or ex_t[:3] in t_raw for ex_t, _ in final_tags): continue
            final_tags.append((t_raw, c)); selected_subterms.update(self.split_base_terms(t_raw))

        return fixed_keywords, [(w, Counter(name_terms)[w]) for w in selected_auto], spec_counts, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

def calculate_seo_metrics(text):
    c_len = len(text)
    try: b_len = len(text.encode('euc-kr'))
    except: b_len = len(text.encode('utf-8'))
    return c_len, b_len

# --- 좌측 사이드바 최적화 구성 ---
with st.sidebar:
    st.header("⚙️ 설정 및 분석")
    
    # 1. 데이터 업로드 그룹 (접고 펼치기 가능)
    with st.expander("📁 데이터 업로드", expanded=True):
        main_file = st.file_uploader("상품 데이터 (CSV)", type=["csv"])
        stats_file = st.file_uploader("판매분석 통계 (Excel/CSV)", type=["csv", "xlsx"])
        target_code = st.text_input("🎯 최적화 상품코드", placeholder="123456789")

    # 2. 전략 키워드 설정 그룹
    with st.expander("🎯 분석 전략 설정", expanded=True):
        conv_in = st.text_input("구매전환 키워드 추가", help="통계 외 추가할 단어")
        add_in = st.text_input("고정 배치 키워드", placeholder="무료배송 등")
        total_kw = st.number_input("목표 키워드 수", value=11, min_value=5)

if main_file:
    try:
        main_file.seek(0)
        df = pd.read_csv(main_file, encoding='cp949')
    except:
        main_file.seek(0)
        df = pd.read_csv(main_file, encoding='utf-8-sig')

    manager = SEOManager(df, [])
    stats_kws = []
    
    if stats_file and target_code:
        try:
            stats_file.seek(0)
            if stats_file.name.endswith('.csv'):
                try: stats_df = pd.read_csv(stats_file, encoding='cp949')
                except: stats_df = pd.read_csv(stats_file, encoding='utf-8-sig')
            else:
                stats_df = pd.read_excel(stats_file, engine='openpyxl')
            stats_kws = manager.extract_stats_keywords(stats_df, target_code)
        except: st.sidebar.error("통계 분석 중 (openpyxl 필요)")

    fixed, auto, specs, tags = manager.run_analysis(stats_kws, conv_in, add_in, total_kw)

    # 1. 상품명 섹션
    st.header("🏷️ 1. 전략적 상품명 조합")
    full_title = " ".join(fixed + [p[0] for p in auto])
    st.code(full_title, language=None)
    c_l, b_l = calculate_seo_metrics(full_title)
    st.markdown(f"**{c_l}자 / {b_l} Byte / {len(fixed)+len(auto)}개 키워드**")
    
    st.markdown("---")
    
    # 2 & 3. 속성 및 태그 (이미지 77c3cc 레이아웃 유지)
    st.header("⚙️ 2. 필터 속성 & 🔍 3. 확장 태그")
    l_col, r_col = st.columns(2)
    with l_col:
        for s_name, _ in specs: st.button(s_name, use_container_width=True, key=f"at_{s_name}")
    with r_col:
        st.success(", ".join([f"#{t[0]}" for t in tags]))
else:
    st.info("좌측 사이드바에서 상품 데이터를 먼저 업로드해주세요.")
