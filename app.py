import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 매니저")
st.markdown("---")

# 2. 전문 SEO 분석 로직 클래스
class SEOManager:
    def __init__(self, df, user_exclude_list):
        self.df = df
        self.exclude_brands = [
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ] + user_exclude_list
        # 분리 기준이 되는 핵심 NLU 단어들 (길이가 긴 단어부터 매칭되도록 정렬)
        self.sub_splits = sorted(['자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', '업소용', '대용량', '전지밀', '식자재', '제과', '제빵', '베이킹'], key=len, reverse=True)

    def split_base_terms(self, text):
        """텍스트를 NLU 규칙에 따라 조각 키워드로 분리하는 핵심 엔진"""
        if pd.isna(text) or text == '-': return []
        
        # 특수문자 제거 및 공백 정규화
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        
        # 정규표현식을 사용하여 sub_splits에 포함된 단어들을 기준으로 강제 분리
        # 예: "맛있는자판기우유" -> ["맛있는", "자판기", "", "우유", ""]
        pattern = f"({'|'.join(self.sub_splits)})"
        raw_parts = re.split(pattern, text)
        
        terms = []
        for part in raw_parts:
            part = part.strip()
            if not part: continue
            
            # 브랜드명이나 숫자가 포함된 조각은 제외
            if part in self.exclude_brands or any(char.isdigit() for char in part):
                continue
                
            # 단어 길이가 2자 이상이거나, NLU 핵심 단어 리스트에 포함된 경우만 수집
            if len(part) > 1 or part in self.sub_splits:
                # 공백이 섞인 경우 다시 한번 쪼개서 넣음
                terms.extend(part.split())
                
        return terms

    def reorder_for_readability(self, word_count_pairs):
        """가독성 그룹별 재배치 (본질->제형->용도->속성)"""
        identity = ['전지', '분유', '우유', '탈지', '전지밀']
        form = ['분말', '가루', '스틱', '액상']
        usage = ['자판기', '업소용', '대용량', '식자재', '제과', '제빵', '베이킹']
        desc = ['진한', '고소한', '맛있는', '추억', '추천', '속편한']

        def get_priority(pair):
            word = pair[0]
            if any(core in word for core in identity): return 1
            if any(core in word for core in form): return 2
            if any(core in word for core in usage): return 3
            if any(core in word for core in desc): return 4
            return 5
        return sorted(word_count_pairs, key=lambda x: get_priority(x))

    def run_analysis(self, conversion_input, add_input, total_target_count):
        # --- 수정 포인트: 수동 입력값도 NLU 분석 엔진(split_base_terms)을 통과하도록 변경 ---
        conv_keys = self.split_base_terms(conversion_input)
        add_keys = self.split_base_terms(add_input)
        fixed_keywords = conv_keys + add_keys
        
        # 상품명에서 빈도수 추출
        name_terms = []
        for name in self.df['상품명']:
            name_terms.extend(self.split_base_terms(name))
        
        name_freq = Counter(name_terms).most_common(50)
        auto_candidates = []
        for w, c in name_freq:
            # 이미 고정 키워드에 포함된 단어는 중복 배제
            if not any(fixed_w == w for fixed_w in fixed_keywords):
                auto_candidates.append((w, c))
        
        remain_count = max(0, total_target_count - len(fixed_keywords))
        selected_auto_pairs = auto_candidates[:remain_count]
        readable_auto_pairs = self.reorder_for_readability(selected_auto_pairs)
        
        # 스펙 분석
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        # 태그 분석 로직
        tag_raw_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                parts = [t.strip() for t in str(tags).split(',')]
                tag_raw_list.extend([t for t in parts if not any(b in t for b in self.exclude_brands)])
        
        tag_freq = Counter(tag_raw_list).most_common(150)
        current_title_words = set(fixed_keywords + [p[0] for p in readable_auto_pairs])
        
        candidates = []
        for t, c in tag_freq:
            if not any(char.isdigit() for char in t) and t not in current_title_words:
                candidates.append((t, c))

        final_tags = []
        top_candidates = candidates[:40]
        for i, (target_t, target_c) in enumerate(top_candidates):
            if len(final_tags) >= 10: break
            is_subsumed = False
            for j, (compare_t, compare_c) in enumerate(top_candidates):
                if i != j and target_t in compare_t and target_t != compare_t:
                    is_subsumed = True; break
            if not is_subsumed:
                if not any(target_t == existing_t for existing_t, _ in final_tags):
                    final_tags.append((target_t, target_c))

        return fixed_keywords, readable_auto_pairs, spec_counts, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

def calculate_seo_metrics(text):
    char_count = len(text)
    try:
        byte_count = len(text.encode('euc-kr'))
    except:
        byte_count = len(text.encode('utf-8'))
    return char_count, byte_count

# 3. GUI 구성
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 전략 키워드 설정")
conversion_input = st.sidebar.text_input("구매전환 키워드", placeholder="예: 맛있는자판기우유")
add_input = st.sidebar.text_input("추가할 키워드 (고정 배치)", placeholder="예: 무료배송당일발송")
exclude_input = st.sidebar.text_input("제외할 키워드 (분석 제외)", placeholder="예: 브랜드명")
total_kw_count = st.sidebar.number_input("상품명 목표 키워드 수", min_value=5, max_value=25, value=11)

user_exclude_list = [w.strip() for w in exclude_input.split() if len(w.strip()) > 0]

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df, user_exclude_list)
    fixed, auto, specs, tags = manager.run_analysis(conversion_input, add_input, total_kw_count)

    st.success("✨ SEO 최적화 분석이 완료되었습니다!")

    # 섹션 1: 상품명
    st.header("🏷️ 1. 전략적 상품명 조합")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("✅ 완성된 상품명")
        # 고정 키워드(fixed)와 자동 키워드(auto) 결합
        full_title = " ".join(fixed + [p[0] for p in auto])
        st.code(full_title, language=None)
        
        total_used_kw = len(fixed) + len(auto)
        c_len, b_len = calculate_seo_metrics(full_title)
        
        if c_len <= 50:
            st.markdown(f"🟢 **정상**: {c_len}자 / {b_len} Byte / {total_used_kw}개 키워드")
        else:
            st.markdown(f"🔴 **주의**: {c_len}자 ({c_len-50}자 초과) / {b_len} Byte / {total_used_kw}개 키워드")
            st.warning("상품명이 50자를 초과하면 검색 결과에서 생략될 수 있습니다.")
            
        st.info("**가독성 전략:** 구매전환 → 제품본질 → 제형 → 용도 → 속성 순 정렬")

    with col2:
        st.subheader("📊 자동 추천 키워드 빈도")
        auto_df = pd.DataFrame(auto, columns=['단어', '빈도'])
        auto_df.index += 1
        st.table(auto_df)

    st.markdown("---")
    # 섹션 2 & 3 (기존 로직 유지)
    st.header("⚙️ 2. 필터 속성 & 🔍 3. 확장 태그")
    t_col1, t_col2 = st.columns(2)
    with t_col1:
        for s, _ in specs: st.button(s, key=f"attr_{s}", use_container_width=True)
    with t_col2:
        tag_display = ", ".join([f"#{t[0]}" for t in tags])
        st.success(tag_display)
else:
    st.info("파일을 업로드하면 정밀 SEO 분석이 시작됩니다.")
