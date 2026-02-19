import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { min-width: 320px; max-width: 320px; }
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

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
        # 복합 명사 분리용 서브 키워드
        self.sub_splits = sorted(['자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', '업소용', '대용량', '멸균', '파우치', '추억', '간식', '재료'], key=len, reverse=True)

    def split_base_terms(self, text, is_manual=False):
        """
        NLU 규칙에 따라 복합 명사를 분리 
        (is_manual=True일 경우 숫자/1글자도 보존하여 사용자 의도 반영)
        """
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        raw_words = text.split()
        terms = []
        pattern = f"({'|'.join(self.sub_splits)})"
        
        for word in raw_words:
            if word in self.exclude_brands: continue
            
            # 수동 입력(is_manual)인 경우 숫자가 포함되어도 허용 (예: 1kg, 2개)
            # 자동 추출인 경우 숫자가 있으면 제외
            if not is_manual and any(char.isdigit() for char in word): continue
            
            parts = re.split(pattern, word)
            for p in parts:
                p = p.strip()
                if not p or p in self.exclude_brands: continue
                
                # 수동 입력은 1글자도 허용, 자동 추출은 2글자 이상만 허용
                if is_manual or len(p) > 1 or p in self.sub_splits:
                    terms.append(p)
        return terms

    def extract_stats_data(self, stats_df, target_product_code):
        """통계 파일에서 특정 상품 코드의 유입 키워드 추출"""
        try:
            # 컬럼명 유연하게 찾기
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
            
            # 상위 5개만 추출 (중복 제거)
            return list(dict.fromkeys(extracted))[:5], existing_name
        except:
            return [], ""

    def reorder_for_readability(self, word_count_pairs):
        """자동 추천 키워드 가독성 정렬"""
        identity, form, usage, desc = ['전지', '분유', '우유', '탈지'], ['분말', '가루', '스틱', '액상'], ['자판기', '업소용', '대용량', '식자재'], ['진한', '고소한', '맛있는', '추억']
        def get_priority(pair):
            word = pair[0]
            if any(core in word for core in identity): return 1
            if any(core in word for core in form): return 2
            if any(core in word for core in usage): return 3
            if any(core in word for core in desc): return 4
            return 5
        return sorted(word_count_pairs, key=lambda x: get_priority(x))

    def run_analysis(self, stats_keywords, fixed_input, conversion_input, total_target_count):
        # 1. 사용자 입력 키워드 처리 (is_manual=True로 보호)
        # fixed_input: "고정 배치"
        # conversion_input: "구매전환 추가"
        manual_fixed = self.split_base_terms(fixed_input, is_manual=True)
        manual_conv = self.split_base_terms(conversion_input, is_manual=True)
        
        # 2. [중요] 순서 결정: 통계 -> 고정 배치 -> 구매전환 추가
        combined_keywords = []
        
        # (1) 통계 키워드
        for k in stats_keywords:
            if k not in combined_keywords: combined_keywords.append(k)
            
        # (2) 고정 배치 키워드
        for k in manual_fixed:
            if k not in combined_keywords: combined_keywords.append(k)
            
        # (3) 구매전환 추가 키워드
        for k in manual_conv:
            if k not in combined_keywords: combined_keywords.append(k)
            
        fixed_result = combined_keywords[:] # 최종 고정 리스트

        # 3. 상품명 자동 추출 (남은 자리 채우기)
        name_terms = []
        for name in self.df['상품명']: name_terms.extend(self.split_base_terms(name))
        name_freq = Counter(name_terms).most_common(100)
        
        auto_candidates = [w for w, c in name_freq if w not in fixed_result]
        remain_count = max(0, total_target_count - len(fixed_result))
        
        selected_auto = auto_candidates[:remain_count]
        readable_auto_pairs = self.reorder_for_readability([(w, Counter(name_terms)[w]) for w in selected_auto])
        
        # 4. 속성 분석
        spec_list = []
        for spec in self.df['스펙'].dropna():
            parts = [p.strip() for p in str(spec).split('|')]
            spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        # 5. 태그 분석 (100% 일치 중복만 제거)
        tag_raw_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-': tag_raw_list.extend([t.strip() for t in str(tags).split(',') if t.strip()])
        tag_freq = Counter(tag_raw_list).most_common(300)
        
        title_keywords = set(fixed_result + [p[0] for p in readable_auto_pairs])
        
        final_tags = []
        for i, (t_raw, c) in enumerate(tag_freq):
            if len(final_tags) >= 10: break
            
            # 기본 필터링: 브랜드 제외, 숫자 제외, 상품명에 있는 단어 제외
            if any(brand in t_raw for brand in self.exclude_brands) or any(char.isdigit() for char in t_raw): continue
            if t_raw in title_keywords: continue 

            # 중복 제거 로직 (100% 일치할 때만 제거)
            is_exact_dup = False
            for existing_t, _ in final_tags:
                if t_raw == existing_t:
                    is_exact_dup = True
                    break
            
            if not is_exact_dup:
                final_tags.append((t_raw, c))

        return fixed_result, readable_auto_pairs, spec_counts, final_tags

def calculate_seo_metrics(text):
    """글자수 및 바이트 수 계산 (네이버 기준)"""
    c_len = len(text)
    try: b_len = len(text.encode('euc-kr'))
    except: b_len = len(text.encode('utf-8'))
    return c_len, b_len

# --- 사이드바 UI ---
with st.sidebar:
    st.subheader("⚙️ 분석 설정")
    with st.expander("📁 1. 데이터 소스", expanded=True):
        uploaded_file = st.file_uploader("상품(CSV)", type=["csv"])
        stats_file = st.file_uploader("통계(XL/CSV)", type=["csv", "xlsx"])
        target_code = st.text_input("🎯 코드", placeholder="상품코드 입력")

    with st.expander("🎯 2. 전략 설정 (순서 중요)", expanded=True):
        st.info("조합 순서: [통계] → [고정] → [구매전환]")
        add_input = st.text_input("📌 고정 배치", placeholder="예: 무료배송")
        conversion_input = st.text_input("➕ 구매전환 추가", placeholder="예: 맛있는")
        total_kw_count = st.number_input("🔢 목표 키워드 수", min_value=5, value=11)
        exclude_input = st.text_input("🚫 제외 키워드", placeholder="브랜드명 등")

    user_exclude = [w.strip() for w in exclude_input.split() if w.strip()]

if uploaded_file:
    # 파일 포인터 초기화 및 로드
    try:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df, user_exclude)
    stats_kws, old_name = [], ""
    
    # 통계 파일 처리
    if stats_file and target_code:
        try:
            stats_file.seek(0)
            if stats_file.name.endswith('.csv'):
                stats_df = pd.read_csv(stats_file, encoding='cp949')
            else:
                stats_df = pd.read_excel(stats_file, engine='openpyxl')
            
            stats_kws, old_name = manager.extract_stats_data(stats_df, target_code)
            if stats_kws: st.sidebar.success(f"✔️ 통계 키워드 {len(stats_kws)}개 확보")
        except Exception as e: 
            st.sidebar.error(f"통계 분석 오류: {e}")

    # 분석 실행 (순서: 통계 -> 고정(add) -> 전환(conv))
    fixed, auto, specs, tags = manager.run_analysis(stats_kws, add_input, conversion_input, total_kw_count)

    # 1. 전략적 상품명 조합
    st.header("🏷️ 1. 전략적 상품명 조합")
    col1, col2 = st.columns([2, 1])
    with col1:
        if old_name: st.info(f"📝 **기존 상품명:** {old_name}")
        st.subheader("✅ 완성된 상품명")
        
        full_title = " ".join(fixed + [p[0] for p in auto])
        c_len, b_len = calculate_seo_metrics(full_title)
        
        # 50자 검증 로직
        if c_len <= 50:
            st.code(full_title, language=None)
            st.markdown(f"🟢 **정상 (50자 이내)**: {c_len}자 / {b_len} Byte")
        else:
            st.code(full_title, language=None)
            st.markdown(f"🔴 **주의 (50자 초과)**: {c_len}자 ({c_len-50}자 초과) / {b_len} Byte")
            st.warning("⚠️ 상품명이 너무 깁니다. 입력한 키워드를 줄이거나 목표 키워드 수를 조절하세요.")

        st.markdown(f"**순서 검증:** `{' + '.join(fixed)}` (통계/고정/전환) + `{' '.join([p[0] for p in auto])}` (자동)")

    with col2:
        st.subheader("📊 자동 추천 빈도")
        st.table(pd.DataFrame(auto, columns=['단어', '빈도']).assign(No=range(1, len(auto)+1)).set_index('No'))

    st.markdown("---")
    # 2. 필터 노출용 속성값
    st.header("⚙️ 2. 필터 노출용 속성값")
    col3, col4 = st.columns([2, 1])
    with col3:
        for s, _ in specs: st.button(s, key=f"attr_{s}", use_container_width=True)
    with col4:
        st.table(pd.DataFrame(specs, columns=['속성값', '빈도']).set_index(pd.Index(range(1, len(specs)+1))))

    st.markdown("---")
    # 3. 확장 검색 태그
    st.header("🔍 3. 확장 검색 태그 (중복 최소화)")
    col5, col6 = st.columns([2, 1])
    with col5:
        st.subheader("✅ 최적화 태그 10선")
        st.success(", ".join([f"#{t[0]}" for t in tags]))
        st.caption("※ 100% 일치하는 태그만 중복으로 처리하여 다양한 키워드 조합을 유지했습니다.")
    with col6:
        st.subheader("📊 태그 사용 빈도수")
        st.table(pd.DataFrame(tags, columns=['태그명', '사용 빈도수']).assign(No=range(1, len(tags)+1)).set_index('No'))
else:
    st.info("좌측 메뉴에서 상품 데이터 파일을 업로드해주세요.")
