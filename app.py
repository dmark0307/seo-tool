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
        """복합 명사를 분리하여 기초 단어(Base Term) 추출"""
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        raw_words = text.split()
        
        terms = []
        sub_splits = ['자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', '업소용', '대용량']
        
        for word in raw_words:
            if word in self.exclude_brands or word.isdigit(): continue
            found_sub = False
            for sub in sub_splits:
                if sub in word and word != sub:
                    terms.append(sub)
                    rem = word.replace(sub, '').strip()
                    if len(rem) > 1: terms.append(rem)
                    found_sub = True
                    break
            if not found_sub and len(word) > 1:
                terms.append(word)
        return terms

    def run_analysis(self):
        # [상품명 분석]
        name_terms = []
        for name in self.df['상품명']:
            name_terms.extend(self.split_base_terms(name))
        name_counts = Counter(name_terms).most_common(20)
        top_12_names = [w for w, c in name_counts[:12]]

        # [속성 분석]
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(10)

        # [태그 분석 - 키워드 확장성 극대화 로직]
        tag_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                parts = [t.strip() for t in str(tags).split(',')]
                tag_list.extend([t for t in parts if not any(b in t for b in self.exclude_brands)])
        
        tag_freq = Counter(tag_list).most_common(100)
        
        # 1단계: 상품명 중복 단어 제거
        candidates = []
        for t, c in tag_freq:
            if not any(word in t for word in top_12_names):
                candidates.append({'tag': t, 'count': c})
        
        # 2단계: 키워드 확장 로직 (A가 B에 포함되면 A를 버리고 B를 유지)
        # 예: '제과제빵'이 '제과제빵재료'에 포함되면 '제과제빵'은 탈락시킴
        tags_to_skip = set()
        for i in range(len(candidates)):
            t1 = candidates[i]['tag']
            for j in range(len(candidates)):
                if i == j: continue
                t2 = candidates[j]['tag']
                # 더 긴 단어가 짧은 단어를 포함하고 있다면 짧은 단어(t1)를 스킵 리스트에 추가
                if t1 in t2:
                    tags_to_skip.add(t1)
                    break
        
        final_pool = [c for c in candidates if c['tag'] not in tags_to_skip]
        
        # 3단계: 최종 빈도수 순으로 10개 선별
        final_tags_with_count = [(c['tag'], c['count']) for c in final_pool[:10]]
        
        return name_counts[:12], spec_counts[:8], final_tags_with_count

# 3. 사용자 인터페이스 및 결과 출력
uploaded_file = st.file_uploader("네이버 쇼핑 분석 결과 CSV 파일을 업로드하세요", type=["csv"])

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
        names, specs, tags = manager.run_analysis()

        st.success("✨ 분석이 완료되었습니다. 키워드 확장성이 극대화된 태그가 선별되었습니다.")

        # --- 섹션 1: 상품명 ---
        st.header("🏷️ 1. 상품명 키워드 (NLU 최적화)")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("✅ 추천 상품명 조합")
            recommended_title = " ".join([n[0] for n in names])
            st.code(recommended_title, language=None)
            st.markdown(f"**NLU 분석 전략:** 가장 유입량이 많은 {len(names)}개의 독립 키워드를 띄어쓰기로 배치했습니다.")
        with col2:
            st.subheader("📊 단어별 빈도")
            name_df = pd.DataFrame(names, columns=['단어', '빈도'])
            st.table(name_df)

        st.markdown("---")

        # --- 섹션 2: 속성 키워드 ---
        st.header("⚙️ 2. 권장 속성 키워드 (필터 검색용)")
        col3, col4 = st.columns([2, 1])
        with col3:
            st.subheader("✅ 필터 최적화 속성")
            for s, c in specs:
                st.button(f"{s}", key=f"attr_{s}", use_container_width=True)
            st.caption("속성란에 위 단어들을 체크하여 필터 검색 유입을 확보하세요.")
        with col4:
            st.subheader("📊 속성 인식 데이터")
            spec_df = pd.DataFrame(specs, columns=['속성값', '빈도'])
            st.table(spec_df)

        st.markdown("---")

        # --- 섹션 3: 검색 태그 ---
        st.header("🔍 3. 확장 검색 태그 (키워드 확장 극대화)")
        col5, col6 = st.columns([2, 1])
        with col5:
            st.subheader("✅ 중복 배제 태그 10선")
            tag_display = ", ".join([f"#{t[0]}" for t in tags])
            st.warning(tag_display)
            st.info("**확장 로직 적용:** '#제과제빵'보다 범위가 넓은 '#제과제빵재료'를 우선 채택하여 검색 범위를 확장했습니다.")
        with col6:
            st.subheader("📊 태그 검색 데이터")
            tag_df = pd.DataFrame(tags, columns=['태그명', '빈도'])
            st.table(tag_df)

        with st.expander("💡 태그 선별 로직 상세 설명 (직원 교육용)"):
            st.write("""
            - **확장형 우선 원칙:** 'A'라는 단어가 'A재료'라는 단어에 포함된다면, 검색 엔진은 'A재료'만으로도 'A'의 의미를 어느 정도 파악할 수 있습니다. 
            - **효율성 극대화:** 따라서 짧은 단어인 '제과제빵'을 버리고 더 긴 '제과제빵재료'를 선택함으로써, 남는 한 자리에 다른 유용한 태그(예: #식자재)를 하나 더 넣을 수 있게 설계했습니다.
            - **결과:** 이 로직을 통해 10개의 태그만으로도 약 15~20개 이상의 키워드 효과를 낼 수 있습니다.
            """)

else:
    st.info("CSV 파일을 업로드하면 분석이 시작됩니다.")
