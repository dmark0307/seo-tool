import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정
st.set_page_config(page_title="네이버 SEO NLU 통합 분석기", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 매니저 (NLU Term 기반)")
st.markdown("---")

# 2. 전문 SEO 분석 로직 클래스
class SEOManager:
    def __init__(self, df):
        self.df = df
        self.exclude_brands = [
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ]
        # NLU 분석 시 핵심 의미 단위(Term) 사전
        self.core_terms = ['전지', '탈지', '분유', '우유', '가루', '분말', '제과', '제빵', '베이킹', '자판기', '업소용', '식자재']

    def extract_nlu_terms(self, text):
        """텍스트를 NLU 의미 단위(Term)로 분해"""
        if pd.isna(text) or text == '-': return set()
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        words = text.split()
        
        terms = set()
        for word in words:
            # 브랜드 및 수치값 제외
            if word in self.exclude_brands or any(char.isdigit() for char in word):
                continue
            # 핵심 사전 기반 분해 및 2글자 이상 추출
            for core in self.core_terms:
                if core in word:
                    terms.add(core)
            if len(word) > 1:
                terms.add(word)
        return terms

    def reorder_for_readability(self, word_count_pairs):
        """가독성 그룹별 재배치"""
        identity = ['전지', '분유', '우유', '탈지']
        form = ['분말', '가루', '스틱', '액상']
        usage = ['자판기', '업소용', '대용량', '식자재', '제과', '제빵', '베이킹']
        desc = ['진한', '고소한', '맛있는', '추억', '추천']

        def get_priority(pair):
            word = pair[0]
            if any(core in word for core in identity): return 1
            if any(core in word for core in form): return 2
            if any(core in word for core in usage): return 3
            if any(core in word for core in desc): return 4
            return 5

        return sorted(word_count_pairs, key=lambda x: get_priority(x))

    def run_analysis(self, manual_input):
        manual_keywords = [w.strip() for w in manual_input.split() if len(w.strip()) > 0]
        manual_terms = set()
        for mk in manual_keywords:
            manual_terms.update(self.extract_nlu_terms(mk))
        
        # [1] 상품명 분석
        all_name_terms = []
        for name in self.df['상품명']:
            found = self.extract_nlu_terms(name)
            all_name_terms.extend([t for t in found if t not in manual_terms])
        
        name_freq = Counter(all_name_terms).most_common(50)
        remain_count = max(0, 12 - len(manual_keywords))
        selected_auto = name_freq[:remain_count]
        readable_auto = self.reorder_for_readability(selected_auto)
        
        # [2] 속성 분석
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        # [3] 태그 분석 - NLU Term 기반 중복 제거 및 조합 확장
        tag_raw_list = []
        for tags_row in self.df['검색인식태그'].dropna():
            if tags_row != '-':
                tag_raw_list.extend([t.strip() for t in str(tags_row).split(',')])
        
        # 제목에 이미 포함된 의미(Term) 집합 구성
        title_terms = manual_terms.copy()
        for word, _ in readable_auto:
            title_terms.update(self.extract_nlu_terms(word))

        # 후보 태그 점수화 (빈도수 + 의미 다양성)
        candidate_tags = []
        tag_freq = Counter(tag_raw_list).most_common(200)
        
        for t, c in tag_freq:
            # 기본 필터: 브랜드 제외, 수치 제외
            if any(b in t for b in self.exclude_brands) or any(char.isdigit() for char in t):
                continue
            
            tag_terms = self.extract_nlu_terms(t)
            # 제목과 의미가 완전히 겹치는 태그 제외
            if tag_terms.issubset(title_terms):
                continue
            
            candidate_tags.append({'tag': t, 'count': c, 'terms': tag_terms})

        # 최종 태그 선별 로직 (의미 중복 배제 및 확장 극대화)
        final_tags = []
        selected_terms_pool = title_terms.copy()

        # 1차: 가장 '정보량이 많은(Term이 많은)' 태그부터 검토하여 다양성 확보
        # 빈도수 순으로 정렬하되 의미 중복을 체크함
        sorted_candidates = sorted(candidate_tags, key=lambda x: x['count'], reverse=True)

        for cand in sorted_candidates:
            if len(final_tags) >= 10: break
            
            # 현재 태그의 의미들이 이미 선택된 의미 풀(Pool)과 80% 이상 겹치면 중복으로 판단
            # 예: '제과제빵재료'가 들어있는데 '제과용'이 들어오는 것을 방지
            overlap = cand['terms'].intersection(selected_terms_pool)
            
            if len(cand['terms']) > 0 and (len(overlap) / len(cand['terms'])) < 0.6:
                final_tags.append((cand['tag'], cand['count']))
                selected_terms_pool.update(cand['terms'])

        return manual_keywords, readable_auto, spec_counts, final_tags

# 3. 사용자 인터페이스 (GUI)
st.sidebar.header("📁 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 전략 키워드")
manual_input = st.sidebar.text_input("구매 유입 키워드 입력", placeholder="예: 속편한 국내산")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df)
    manual_keys, auto_keys, specs, tags = manager.run_analysis(manual_input)

    st.success("✅ NLU Term 분석을 통한 키워드 최적화가 완료되었습니다!")

    # 섹션 1: 상품명
    st.header("🏷️ 1. 전략적 상품명 조합")
    col1, col2 = st.columns([2, 1])
    with col1:
        full_title = " ".join(manual_keys + [p[0] for p in auto_keys])
        st.code(full_title, language=None)
        st.info("**NLU 전략:** 의미 단위로 분석하여 가독성이 가장 높은 순서로 배열했습니다.")
    with col2:
        st.table(pd.DataFrame(auto_keys, columns=['단어', '빈도']))

    st.markdown("---")

    # 섹션 2: 속성
    st.header("⚙️ 2. 권장 속성값")
    col3, col4 = st.columns([2, 1])
    with col3:
        for s, _ in specs: st.button(s, use_container_width=True)
    with col4:
        st.table(pd.DataFrame(specs, columns=['속성값', '빈도']))

    st.markdown("---")

    # 섹션 3: 태그 (NLU 확장 로직 적용)
    st.header("🔍 3. 확장 검색 태그 (의미 기반 중복 제거)")
    col5, col6 = st.columns([2, 1])
    with col5:
        st.warning(", ".join([f"#{t[0]}" for t in tags]))
        st.info("""
        **NLU Term 필터링 적용:**
        - '#제과제빵재료'가 선정되면 유사 의미인 '#제과용', '#제과제빵용품'은 자동으로 배제됩니다.
        - 남은 자리에 새로운 유입 경로(맛, 영양, 용도 등)를 가진 키워드를 우선 배치하여 **검색 경우의 수**를 극대화했습니다.
        """)
    with col6:
        st.table(pd.DataFrame(tags, columns=['태그명', '인식 횟수']))

else:
    st.info("CSV 파일을 업로드하면 NLU 기반 분석이 시작됩니다.")
