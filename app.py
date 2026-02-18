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
        self.exclude_brands = set([
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ] + user_exclude_list)
        # NLU 분리 기준 단어 리스트 (긴 단어부터 매칭하여 오차 방지)
        self.sub_splits = sorted([
            '자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', 
            '업소용', '대용량', '식자재', '제과', '제빵', '베이킹', '멸균', '파우치', '전지밀'
        ], key=len, reverse=True)

    def split_base_terms(self, text):
        """복합 명사를 NLU 규칙에 따라 조각 키워드로 분리하는 핵심 엔진"""
        if pd.isna(text) or text == '-': return []
        
        # 1. 특수문자 제거 및 공백 정규화
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        
        # 2. 정규표현식 패턴 생성 (이미 정의된 핵심 키워드 기준)
        pattern = f"({'|'.join(self.sub_splits)})"
        
        # 3. 텍스트 분리 실행
        raw_parts = re.split(pattern, text)
        
        terms = []
        for part in raw_parts:
            p = part.strip()
            if not p: continue
            
            # 브랜드명이나 숫자가 포함된 조각은 제외
            if p in self.exclude_brands or any(c.isdigit() for c in p):
                continue
                
            # 단어 길이가 2자 이상이거나, NLU 핵심 단어 리스트에 포함된 경우 수집
            if len(p) > 1 or p in self.sub_splits:
                # 내부 공백이 있을 경우 다시 쪼개어 추가
                terms.extend(p.split())
                
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
        # --- 수정 포인트: 수동 입력값에도 NLU 분리 엔진 적용 ---
        conv_keys = self.split_base_terms(conversion_input)
        add_keys = self.split_base_terms(add_input)
        fixed_keywords = conv_keys + add_keys
        
        # 상품명 기반 빈도 분석
        name_terms = []
        for name in self.df['상품명']:
            name_terms.extend(self.split_base_terms(name))
        
        name_freq = Counter(name_terms).most_common(50)
        auto_candidates = []
        for w, c in name_freq:
            # 완전 일치 비교로 중복 제거
            if w not in fixed_keywords:
                auto_candidates.append((w, c))
        
        remain_count = max(0, total_target_count - len(fixed_keywords))
        selected_auto_pairs = auto_candidates[:remain_count]
        readable_auto_pairs = self.reorder_for_readability(selected_auto_pairs)
        
        # 스펙 및 태그 분석 로직
        spec_list = []
        for spec in self.df['스펙'].dropna():
            parts = [p.strip() for p in str(spec).split('|') if len(p.strip()) > 1]
            spec_list.extend([p for p in parts if p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        tag_raw_list = []
        for row in self.df['검색인식태그'].dropna():
            tag_raw_list.extend([t.strip() for t in str(row).split(',') if t.strip()])
        
        tag_freq = Counter(tag_raw_list).most_common(150)
        current_title_set = set(fixed_keywords + [p[0] for p in readable_auto_pairs])
        
        # 태그 후보 선별 (중복 제거 및 수식어 다양화)
        candidates = [(t, c) for t, c in tag_freq if not any(c.isdigit() for c in t) and t not in current_title_set]
        final_tags = []
        top_candidates = candidates[:40]
        
        for i, (target_t, target_c) in enumerate(top_candidates):
            if len(final_tags) >= 10: break
            # 포함 관계 및 수식어 중복 배제 (확장성 전략)
            prefix = target_t[:3] if len(target_t) > 3 else target_t[:2]
            is_redundant = False
            for ex_t, _ in final_tags:
                if prefix in ex_t or any(ex_t[:3] in target_t for ex_t, _ in final_tags if len(ex_t) > 2):
                    is_redundant = True; break
                if target_t in ex_t: is_redundant = True; break
            
            if not is_redundant:
                final_tags.append((target_t, target_c))

        return fixed_keywords, readable_auto_pairs, spec_counts, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

def calculate_seo_metrics(text):
    char_count = len(text)
    try: byte_count = len(text.encode('euc-kr'))
    except: byte_count = len(text.encode('utf-8'))
    return char_count, byte_count

# 3. GUI 구성
st.sidebar.header("🎯 전략 키워드 설정")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 업로드", type=["csv"])
conversion_input = st.sidebar.text_input("구매전환 키워드", placeholder="예: 맛있는자판기우유")
add_input = st.sidebar.text_input("추가할 키워드", placeholder="예: 무료배송당일발송")
total_kw_count = st.sidebar.number_input("목표 키워드 수", min_value=5, max_value=25, value=11)

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df, [])
    fixed, auto, specs, tags = manager.run_analysis(conversion_input, add_input, total_kw_count)

    st.header("🏷️ 1. 전략적 상품명 조합")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("✅ 완성된 상품명")
        full_title = " ".join(fixed + [p[0] for p in auto])
        st.code(full_title, language=None)
        
        c_len, b_len = calculate_seo_metrics(full_title)
        total_used_kw = len(fixed) + len(auto)
        
        status = "🟢 정상" if c_len <= 50 else "🔴 주의"
        st.markdown(f"**{status}**: {c_len}자 / {b_len} Byte / {total_used_kw}개 키워드")
        st.info("**NLU 규칙 적용:** 입력하신 키워드가 자동으로 분리 및 정렬되었습니다.")

    with col2:
        st.subheader("📊 자동 추천 빈도")
        st.table(pd.DataFrame(auto, columns=['단어', '빈도']).assign(No=range(1, len(auto)+1)).set_index('No'))

    st.markdown("---")
    
    # 이미지 77c3cc 레이아웃 적용
    st.header("⚙️ 2. 필터 속성 & 🔍 3. 확장 태그")
    l_col, r_col = st.columns(2)
    with l_col:
        for s_name, _ in specs:
            st.button(s_name, use_container_width=True, key=f"attr_{s_name}")
    with r_col:
        tag_str = ", ".join([f"#{t[0]}" for t in tags])
        st.success(tag_str)
        st.caption("※ 중복 수식어를 배제하고 유입 경로를 극대화한 태그입니다.")
else:
    st.info("파일을 업로드하면 정밀 SEO 분석이 시작됩니다.")
