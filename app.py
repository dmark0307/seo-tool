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
        # NLU 분석 시 주요하게 쪼개야 할 키워드
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

        # [태그 분석]
        tag_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                parts = [t.strip() for t in str(tags).split(',')]
                tag_list.extend([t for t in parts if not any(b in t for b in self.exclude_brands)])
        
        # 상품명과 중복되지 않는 태그 선별
        tag_freq = Counter(tag_list).most_common(50)
        final_tags_with_count = []
        for t, c in tag_freq:
            if len(final_tags_with_count) >= 10: break
            if not any(word in t for word in top_12_names):
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

        st.success("✨ 분석이 완료되었습니다. 각 항목별 빈도수와 SEO 전략을 확인하세요.")

        # --- 섹션 1: 상품명 ---
        st.header("🏷️ 1. 상품명 키워드 (NLU 최적화)")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("✅ 추천 상품명 조합")
            recommended_title = " ".join([n[0] for n in names])
            st.code(recommended_title, language=None)
            st.markdown(f"**글자수:** 약 {len(recommended_title)}자 (공백 포함)")
        with col2:
            st.subheader("📊 단어별 노출 빈도")
            name_df = pd.DataFrame(names, columns=['단어', '노출횟수'])
            st.table(name_df)
        
        with st.expander("💡 상품명 키워드 배치 전략 설명"):
            st.write("""
            - **분석 원리:** 다른 판매자들이 상품명에 가장 많이 사용한 단어들을 '의미 단위(Term)'로 쪼개어 분석했습니다.
            - **전략:** 네이버 NLU 엔진은 '자판기우유'보다 **'자판기 우유'**와 같이 띄어쓰기된 형태를 더 명확하게 인식하며, 단어의 조합 검색 확률을 높여줍니다.
            - **주의사항:** 빈도수가 높은 단어를 전면에 배치할수록 클릭률과 검색 연관성 점수가 상승합니다.
            """)

        st.markdown("---")

        # --- 섹션 2: 속성 키워드 ---
        st.header("⚙️ 2. 권장 속성 키워드 (필터 최적화)")
        col3, col4 = st.columns([2, 1])
        with col3:
            st.subheader("✅ 주요 속성값 리스트")
            st.write("아래 키워드를 스마트스토어 등록 시 **'속성'**란에 검색하여 체크하세요.")
            for s, c in specs:
                st.button(f"{s} (검색 인식: {c}회)", key=s)
        with col4:
            st.subheader("📊 속성별 빈도 데이터")
            spec_df = pd.DataFrame(specs, columns=['속성값', '빈도'])
            st.table(spec_df)

        with st.expander("💡 속성 키워드 활용 전략 설명"):
            st.write("""
            - **분석 원리:** 상위 노출 상품들의 '스펙' 항목에 실제로 등록되어 네이버 필터 검색에 잡힌 데이터입니다.
            - **전략:** 상품명에 단어를 낭비하지 말고, 이 키워드들을 **속성값**으로 입력하세요. 
            - **효과:** 소비자가 쇼핑 화면 좌측에서 '실온보관', '파우치' 등의 필터를 클릭했을 때 내 상품이 노출되는 핵심 근거가 됩니다.
            """)

        st.markdown("---")

        # --- 섹션 3: 검색 태그 ---
        st.header("🔍 3. 확장 검색 태그 (유입 그물망 확장)")
        col5, col6 = st.columns([2, 1])
        with col5:
            st.subheader("✅ 중복 없는 태그 10선")
            tag_display = ", ".join([f"#{t[0]}" for t in tags])
            st.info(tag_display)
        with col6:
            st.subheader("📊 태그별 빈도 데이터")
            tag_df = pd.DataFrame(tags, columns=['태그명', '빈도'])
            st.table(tag_df)

        with st.expander("💡 태그 키워드 확장 전략 설명"):
            st.write("""
            - **분석 원리:** 상품명과 속성에 사용된 단어를 제외하고, **태그 사전**에 등록되어 실제 유입을 만들어낸 단어들입니다.
            - **전략:** 상품명과 겹치지 않는 단어를 태그에 넣어야 검색 그물(Coverage)이 넓어집니다. 
            - **효과:** '전지분유'를 검색한 사람뿐만 아니라 '홈베이킹재료', '추억의맛'을 검색한 잠재 고객까지 내 상품으로 끌어들입니다.
            """)

else:
    st.info("사이드바 또는 중앙의 업로더를 통해 다른 판매자의 상품 분석 CSV 파일을 업로드해주세요.")
