import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 매니저")
st.markdown("---")

class SEOManager:
    def __init__(self, df, user_exclude_list):
        self.df = df
        self.exclude_brands = set([
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ] + user_exclude_list)
        # NLU 분리 기준 단어 리스트 (긴 단어부터 매칭)
        self.sub_splits = sorted([
            '자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', 
            '업소용', '대용량', '식자재', '제과', '제빵', '베이킹', '멸균', '파우치'
        ], key=len, reverse=True)

    def split_base_terms(self, text):
        """붙여 쓴 키워드도 NLU 규칙에 따라 자동으로 쪼개주는 엔진"""
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        
        # 패턴 기반 강제 분리 (예: 맛있는자판기우유 -> 맛있는 자판기 우유)
        pattern = f"({'|'.join(self.sub_splits)})"
        raw_parts = re.split(pattern, text)
        
        terms = []
        for part in raw_parts:
            p = part.strip()
            if not p or p in self.exclude_brands or any(c.isdigit() for c in p): continue
            if len(p) > 1 or p in self.sub_splits:
                terms.extend(p.split())
        return terms

    def reorder_for_readability(self, word_count_pairs):
        identity, form, usage, desc = ['전지', '분유', '우유', '탈지'], ['분말', '가루', '스틱', '액상'], ['자판기', '업소용', '대용량', '식자재'], ['진한', '고소한', '맛있는', '추억']
        def get_priority(pair):
            w = pair[0]
            if any(c in w for c in identity): return 1
            if any(c in w for c in form): return 2
            if any(c in w for c in usage): return 3
            if any(c in w for c in desc): return 4
            return 5
        return sorted(word_count_pairs, key=lambda x: get_priority(x))

    def run_analysis(self, conv_input, add_input, total_count):
        # 수동 입력 키워드도 NLU 분리 적용
        conv_keys = self.split_base_terms(conv_input)
        add_keys = self.split_base_terms(add_input)
        fixed_keywords = conv_keys + add_keys
        
        name_terms = []
        for name in self.df['상품명']: name_terms.extend(self.split_base_terms(name))
        name_freq = Counter(name_terms).most_common(50)
        
        auto_candidates = [(w, c) for w, c in name_freq if w not in fixed_keywords]
        readable_auto = self.reorder_for_readability(auto_candidates[:max(0, total_count - len(fixed_keywords))])
        
        # [이미지 77c3cc 재현] 스펙 분석
        spec_list = []
        for spec in self.df['스펙'].dropna():
            parts = [p.strip() for p in str(spec).split('|') if len(p.strip()) > 1]
            spec_list.extend([p for p in parts if p not in self.exclude_brands])
        specs = Counter(spec_list).most_common(8)

        # [이미지 77c3cc 재현] 태그 분석 (수식어 중복 배제)
        tag_raw = []
        for row in self.df['검색인식태그'].dropna():
            tag_raw.extend([t.strip() for t in str(row).split(',') if t.strip()])
        
        tag_freq_map = Counter(tag_raw)
        title_set = set(fixed_keywords + [p[0] for p in readable_auto])
        candidates = [(t, c) for t, c in tag_freq_map.most_common(150) if t not in title_set and not any(c.isdigit() for c in t)]

        final_tags = []
        used_prefixes = set()
        for t, c in candidates:
            if len(final_tags) >= 10: break
            prefix = t[:3] if len(t) > 3 else t[:2]
            if not any(prefix in ex_t or ex_t[:3] in t for ex_t, _ in final_tags):
                final_tags.append((t, c))
        
        return conv_keys, add_keys, readable_auto, specs, final_tags

def check_metrics(text):
    c_len = len(text)
    try: b_len = len(text.encode('euc-kr'))
    except: b_len = len(text.encode('utf-8'))
    return c_len, b_len

# 3. GUI 구성
st.sidebar.header("🎯 설정")
uploaded_file = st.sidebar.file_uploader("CSV 업로드", type=["csv"])
conv_in = st.sidebar.text_input("구매전환 키워드", placeholder="맛있는자판기우유")
add_in = st.sidebar.text_input("추가 키워드")
total_kw = st.sidebar.number_input("목표 키워드 수", value=11)

if uploaded_file:
    try: df = pd.read_csv(uploaded_file, encoding='cp949')
    except: df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df, [])
    conv, add, auto, specs, tags = manager.run_analysis(conv_in, add_in, total_kw)

    # 섹션 1: 상품명
    st.header("🏷️ 1. 전략적 상품명 조합")
    full_title = " ".join(conv + add + [p[0] for p in auto])
    st.code(full_title, language=None)
    
    c_l, b_l = check_metrics(full_title)
    kw_c = len(conv) + len(add) + len(auto)
    st.markdown(f"{'🟢 정상' if c_l <= 50 else '🔴 주의'}: **{c_l}자 / {b_l} Byte / {kw_c}개 키워드**")
    
    st.markdown("---")

    # [이미지 77c3cc 레이아웃 재현] 섹션 2 & 3 통합 출력
    st.header("⚙️ 2. 필터 속성 & 🔍 3. 확장 태그")
    col_left, col_right = st.columns([1, 1])

    with col_left:
        # 왼쪽: 필터 속성 버튼 리스트
        for s_name, _ in specs:
            st.button(s_name, use_container_width=True, key=f"btn_{s_name}")

    with col_right:
        # 오른쪽: 연록색 박스 내 태그 리스트
        tag_string = ", ".join([f"#{t[0]}" for t in tags])
        st.success(tag_string)

else:
    st.info("사이드바에서 파일을 업로드해주세요.")
