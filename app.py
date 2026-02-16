import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정
st.set_page_config(page_title="네이버 SEO 통합 분석 도구", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 매니저")
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

    def split_base_terms(self, text):
        """복합 명사를 분리하여 기초 단어(Base Term) 추출 및 수치값/브랜드 제거"""
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        raw_words = text.split()
        
        terms = []
        sub_splits = ['자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', '업소용', '대용량']
        
        for word in raw_words:
            if word in self.exclude_brands or any(char.isdigit() for char in word):
                continue
            
            found_sub = False
            for sub in sub_splits:
                if sub in word and word != sub:
                    terms.append(sub)
                    rem = word.replace(sub, '').strip()
                    if len(rem) > 1 and not any(char.isdigit() for char in rem):
                        terms.append(rem)
                    found_sub = True
                    break
            if not found_sub and len(word) > 1:
                terms.append(word)
        return terms

    def reorder_for_readability(self, words):
        """AI 분석 단어를 가독성 높은 순서로 재배치"""
        # 그룹 정의
        identity = ['전지', '분유', '우유', '탈지', '전지밀'] # 제품 본질
        form = ['분말', '가루', '스틱', '액상'] # 제형
        usage = ['자판기', '업소용', '대용량', '식자재', '제과', '제빵', '베이킹'] # 용도
        desc = ['진한', '고소한', '맛있는', '추억', '추천', '속편한'] # 맛/속성/감성

        def get_priority(word):
            if any(core in word for core in identity): return 1
            if any(core in word for core in form): return 2
            if any(core in word for core in usage): return 3
            if any(core in word for core in desc): return 4
            return 5

        # 우선순위 그룹별로 정렬하되, 그룹 내에서는 기존 빈도순 유지
        return sorted(words, key=lambda x: get_priority(x))

    def run_analysis(self, manual_input):
        manual_keywords = [w.strip() for w in manual_input.split() if len(w.strip()) > 0]
        
        name_terms = []
        for name in self.df['상품명']:
            name_terms.extend(self.split_base_terms(name))
        
        name_freq = Counter(name_terms).most_common(50)
        
        # 중복 제거 및 후보 선별
        auto_candidates = []
        for w, c in name_freq:
            if not any(manual_w in w or w in manual_w for manual_w in manual_keywords):
                auto_names_only = w # 단어만 추출
                auto_candidates.append(w)
        
        # 12단어 중 남은 수량만큼 선별
        remain_count = max(0, 12 - len(manual_keywords))
        selected_auto = auto_candidates[:remain_count]
        
        # [핵심] 가독성 재배치 적용
        readable_auto = self.reorder_for_readability(selected_auto)
        
        # 속성 및 태그 로직
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        tag_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                parts = [t.strip() for t in str(tags).split(',')]
                tag_list.extend([t for t in parts if not any(b in t for b in self.exclude_brands)])
        
        tag_freq = Counter(tag_list).most_common(100)
        current_title_words = manual_keywords + readable_auto
        
        candidates = []
        for t, c in tag_freq:
            if not any(char.isdigit() for char in t) and not any(word in t for word in current_title_words):
                candidates.append({'tag': t, 'count': c})
        
        tags_to_skip = set()
        for i in range(len(candidates)):
            t1 = candidates[i]['tag']
            for j in range(len(candidates)):
                if i == j: continue
                t2 = candidates[j]['tag']
                if t1 in t2:
                    tags_to_skip.add(t1)
                    break
        
        final_pool = [c for c in candidates if c['tag'] not in tags_to_skip]
        final_tags = [(c['tag'], c['count']) for c in final_pool[:10]]
        
        return manual_keywords, readable_auto, spec_counts, final_tags

# 3. 사용자 인터페이스 (GUI)
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 수동 키워드 설정")
manual_input = st.sidebar.text_input(
    "실제 구매 유입 키워드 입력", 
    placeholder="예: 맛있는 속편한 국내산",
    help="이 키워드는 상품명 맨 앞에 고정되며, 가독성 재배치 로직이 적용되지 않고 입력한 순서대로 유지됩니다."
)

if uploaded_file:
    df = None
    try:
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")

    if df is not None:
        manager = SEOManager(df)
        manual_keys, auto_keys, specs, tags = manager.run_analysis(manual_input)

        st.success("✨ 가독성 최적화 분석이 완료되었습니다!")

        # --- 섹션 1: 상품명 ---
        st.header("🏷️ 1. 전략적 상품명 조합 (가독성 재배치 반영)")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("✅ 완성된 상품명")
            full_title = " ".join(manual_keys + auto_keys)
            st.code(full_title, language=None)
            st.info("**가독성 로직:** [수동입력] + [제품본질] + [제형] + [용도] + [속성] 순으로 배치되어 소비자가 읽기 가장 편안한 구조입니다.")
        
        with col2:
            st.subheader("📊 자동 선별 키워드 리스트")
            # 가독성 순서대로 표기
            st.table(pd.DataFrame(auto_keys, columns=['재배치된 단어']))

        st.markdown("---")

        # --- 섹션 2: 속성 키워드 ---
        st.header("⚙️ 2. 필터 노출용 속성값")
        col3, col4 = st.columns([2, 1])
        with col3:
            st.subheader("✅ 권장 속성 리스트")
            for s, c in specs:
                st.button(f"{s}", key=f"attr_{s}", use_container_width=True)
        with col4:
            st.subheader("📊 속성 인식 데이터")
            spec_df = pd.DataFrame(specs, columns=['속성값', '빈도'])
            st.table(spec_df)

        st.markdown("---")

        # --- 섹션 3: 확장 태그 ---
        st.header("🔍 3. 확장 검색 태그")
        col5, col6 = st.columns([2, 1])
        with col5:
            st.subheader("✅ 최종 태그 10선")
            tag_display = ", ".join([f"#{t[0]}" for t in tags])
            st.warning(tag_display)
        with col6:
            st.subheader("📊 태그 인식 데이터")
            tag_df = pd.DataFrame(tags, columns=['태그명', '빈도'])
            st.table(tag_df)

        with st.expander("💡 [매니저 필독] 가독성 재배치 원리"):
            st.write("""
            1. **수동 키워드 존중:** 대표님이 직접 입력하신 단어는 의도가 명확하므로 순서 변경 없이 맨 앞에 배치합니다.
            2. **AI 키워드 그룹화:** AI가 뽑은 핵심 단어들을 아래 순서로 자동 재정렬합니다.
                - **1순위 (본질):** 전지, 분유, 우유 등 상품의 정체성
                - **2순위 (형태):** 분말, 가루, 스틱 등 외형적 특징
                - **3순위 (용도):** 자판기, 업소용, 베이킹 등 구매 목적
                - **4순위 (속성):** 진한, 고소한, 추억 등 감성/풍미
            3. **결과:** 검색 로직(SEO)을 만족하면서도 고객이 읽었을 때 문장이 매끄러워 구매 전환율이 높아집니다.
            """)
else:
    st.info("왼쪽 사이드바에서 파일을 업로드하고 구매 키워드를 입력해 보세요.")
