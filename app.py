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
        # 지재권 보호를 위한 필터링 리스트
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

        # [태그 분석 - 확장 및 중복 배제 로직 강화]
        tag_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                parts = [t.strip() for t in str(tags).split(',')]
                tag_list.extend([t for t in parts if not any(b in t for b in self.exclude_brands)])
        
        tag_freq = Counter(tag_list).most_common(60)
        final_tags_with_count = []
        
        for t, c in tag_freq:
            if len(final_tags_with_count) >= 10: break
            
            # 1. 상품명 키워드와 중복되는지 체크
            if any(word in t for word in top_12_names):
                continue
            
            # 2. 이미 선택된 태그들과 중복/포함 관계인지 체크 (확장성 고려)
            is_redundant = False
            for existing_t, _ in final_tags_with_count:
                # 신규 태그가 기존 태그를 포함하거나, 기존 태그가 신규 태그를 포함하는지 (예: 제과제빵 vs 제과제빵재료)
                if t in existing_t or existing_t in t:
                    is_redundant = True
                    break
            
            if not is_redundant:
                final_tags_with_count.append((t, c))
        
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

        st.success("✨ 분석이 완료되었습니다. 단어 간 중복을 제거하여 검색 범위를 극대화했습니다.")

        # --- 섹션 1: 상품명 ---
        st.header("🏷️ 1. 상품명 키워드 (NLU 최적화)")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("✅ 추천 상품명 조합")
            recommended_title = " ".join([n[0] for n in names])
            st.code(recommended_title, language=None)
            st.info(f"**NLU 분석 결과:** 총 {len(names)}개의 핵심 유입 단어가 선정되었습니다.")
        with col2:
            st.subheader("📊 단어별 사용 빈도")
            name_df = pd.DataFrame(names, columns=['단어', '빈도(회)'])
            st.table(name_df)
        
        with st.expander("💡 상품명 전략 상세 설명"):
            st.write(f"""
            - **사용 단어 수:** {len(names)}단어 (네이버 nluterms 권장 기준 10~12단어 준수)
            - **분석 내용:** 수집된 {len(df)}개 상품명 데이터에서 가장 많이 사용된 단어를 추출했습니다.
            - **적용 로직:** 띄어쓰기를 통해 각 단어가 독립적인 '텀(Term)'으로 인식되게 하여, 검색 조합(예: '{names[0][0]} + {names[1][0]}') 노출을 극대화합니다.
            """)

        st.markdown("---")

        # --- 섹션 2: 속성 키워드 ---
        st.header("⚙️ 2. 권장 속성 키워드 (필터 최적화)")
        col3, col4 = st.columns([2, 1])
        with col3:
            st.subheader("✅ 필터 노출용 속성값")
            for s, c in specs:
                st.button(f"{s}", key=s, use_container_width=True)
            st.caption("스마트스토어 등록 페이지의 '속성'란에서 위 키워드를 찾아 선택하세요.")
        with col4:
            st.subheader("📊 속성 인식 빈도")
            spec_df = pd.DataFrame(specs, columns=['속성명', '인식 횟수'])
            st.table(spec_df)

        with st.expander("💡 속성 전략 상세 설명"):
            st.write(f"""
            - **분석 내용:** 실제 검색 결과 상위 상품들이 공통적으로 네이버 쇼핑 '스펙'란에 등록한 데이터입니다.
            - **적용 로직:** 소비자가 '멸균', '실온보관' 등의 조건을 선택해 검색할 때(필터 쇼핑), 상품명에 해당 단어가 없어도 속성값만으로 노출 점수를 얻습니다.
            - **클레임 방지:** 가장 많이 사용된 상위 속성값 위주로 선별하여 표준적인 정보 등록을 유도합니다.
            """)

        st.markdown("---")

        # --- 섹션 3: 검색 태그 ---
        st.header("🔍 3. 확장 검색 태그 (중복 배제 및 조합 확장)")
        col5, col6 = st.columns([2, 1])
        with col5:
            st.subheader("✅ 최적화 태그 10선")
            tag_display = ", ".join([f"#{t[0]}" for t in tags])
            st.warning(tag_display)
            st.info(f"**알고리즘 적용:** 유사 단어(예: {tags[0][0] if tags else ''} 계열) 중복을 차단하여 유입 경로를 다각화했습니다.")
        with col6:
            st.subheader("📊 태그 검색 인식 빈도")
            tag_df = pd.DataFrame(tags, columns=['태그명', '인식 횟수'])
            st.table(tag_df)

        with st.expander("💡 태그 확장 전략 상세 설명"):
            st.write("""
            - **중복 배제 로직:** `#제과제빵`과 `#제과제빵재료`처럼 의미가 겹치는 경우, 하나만 선택하고 남은 자리에 다른 유의미한 키워드(예: #식자재)를 배치했습니다.
            - **조합 확장:** 상품명(Title)에서 잡지 못한 잠재적 검색어(용도, 타겟, 상황)를 태그로 보완합니다.
            - **노출 효과:** 검색 엔진이 상품의 카테고리를 더 넓게 인식하도록 유도하여, 비인기 검색어(Long-tail keyword) 유입을 창출합니다.
            """)

else:
    st.info("사이드바 또는 중앙의 업로더를 통해 분석용 CSV 파일을 업로드해주세요.")
