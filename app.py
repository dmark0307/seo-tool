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
        """복합 명사를 분리하여 기초 단어(Base Term) 추출 및 수치값 제거"""
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        raw_words = text.split()
        
        terms = []
        sub_splits = ['자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', '업소용', '대용량']
        
        for word in raw_words:
            # [수정] 브랜드명 제외 + 숫자가 포함된 단어(1kg, 20kg 등) 전체 제외
            if word in self.exclude_brands or any(char.isdigit() for char in word):
                continue
            
            found_sub = False
            for sub in sub_splits:
                if sub in word and word != sub:
                    terms.append(sub)
                    rem = word.replace(sub, '').strip()
                    # 분리된 단어에도 숫자가 있으면 제외
                    if len(rem) > 1 and not any(char.isdigit() for char in rem):
                        terms.append(rem)
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

        # [태그 분석 - 확장성 및 중복 제거]
        tag_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                parts = [t.strip() for t in str(tags).split(',')]
                tag_list.extend([t for t in parts if not any(b in t for b in self.exclude_brands)])
        
        tag_freq = Counter(tag_list).most_common(100)
        
        candidates = []
        for t, c in tag_freq:
            # 태그에서도 숫자가 포함된 경우 제외 (클레임 방지)
            if not any(char.isdigit() for char in t) and not any(word in t for word in top_12_names):
                candidates.append({'tag': t, 'count': c})
        
        # 키워드 확장 로직 (포함 관계 정리)
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

        st.success("✨ 분석이 완료되었습니다. 수치값이 제거된 안전한 키워드들이 선별되었습니다.")

        # --- 섹션 1: 상품명 ---
        st.header("🏷️ 1. 상품명 키워드 (클레임 방지 최적화)")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("✅ 추천 상품명 조합")
            recommended_title = " ".join([n[0] for n in names])
            st.code(recommended_title, language=None)
            st.info("**업데이트:** '1kg', '20kg', '10T'와 같은 수치값을 제거하여 오기재로 인한 클레임을 원천 차단했습니다.")
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
            st.caption("속성값에는 정확한 수치를 입력해야 하므로, 수동으로 확인 후 체크하세요.")
        with col4:
            st.subheader("📊 속성 인식 데이터")
            spec_df = pd.DataFrame(specs, columns=['속성값', '빈도'])
            st.table(spec_df)

        st.markdown("---")

        # --- 섹션 3: 검색 태그 ---
        st.header("🔍 3. 확장 검색 태그 (조합 확장)")
        col5, col6 = st.columns([2, 1])
        with col5:
            st.subheader("✅ 중복 배제 태그 10선")
            tag_display = ", ".join([f"#{t[0]}" for t in tags])
            st.warning(tag_display)
        with col6:
            st.subheader("📊 태그 검색 데이터")
            tag_df = pd.DataFrame(tags, columns=['태그명', '빈도'])
            st.table(tag_df)

        with st.expander("💡 필터링 로직 설명"):
            st.write("""
            - **수치값 자동 제거:** 단어에 숫자가 하나라도 포함되어 있으면(예: 1kg, 200ml) 상품명과 태그 후보에서 제외합니다.
            - **이유:** 상품명에 포함된 잘못된 수치는 반품 및 클레임의 직접적인 원인이 되기 때문입니다.
            - **속성 활용:** 정확한 수치 정보는 상품명이 아닌 '속성'란과 '상세페이지'에서 정확히 기재하는 것이 SEO와 고객 응대 모두에 유리합니다.
            """)

else:
    st.info("CSV 파일을 업로드하면 수치값을 제외한 SEO 분석이 시작됩니다.")
