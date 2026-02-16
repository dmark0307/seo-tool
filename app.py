import streamlit as st
import pandas as pd
import re
from collections import Counter
import io

# 1. 페이지 설정
st.set_page_config(page_title="사내 SEO 통합 분석기", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 도구")
st.markdown("---")

# 2. 전문 SEO 분석 로직 클래스
class SEOManager:
    def __init__(self, df):
        self.df = df
        # 지재권 보호를 위한 필터링 리스트 (추가 가능)
        self.exclude_brands = [
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ]

    def split_words(self, text):
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        return [w for w in text.split() if len(w) > 1 and w not in self.exclude_brands and not w.isdigit()]

    def run_analysis(self):
        # [A] 상품명 분석 (NLU 기반 핵심 단어)
        all_names = []
        for name in self.df['상품명']:
            all_names.extend(self.split_words(name))
        top_12_names = [w for w, c in Counter(all_names).most_common(12)]

        # [B] 속성 분석 (스펙 컬럼 데이터 활용)
        all_specs = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                all_specs.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        top_specs = [w for w, c in Counter(all_specs).most_common(8)]

        # [C] 태그 분석 (검색인식태그 및 확장성 고려)
        all_tags = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                parts = [t.strip() for t in str(tags).split(',')]
                all_tags.extend([t for t in parts if not any(b in t for b in self.exclude_brands)])
        
        final_tags = []
        for t in [w for w, c in Counter(all_tags).most_common(50)]:
            if len(final_tags) >= 10: break
            # 상품명과 중복되지 않는 키워드만 선별
            if not any(word in t for word in top_12_names):
                final_tags.append(t)
        
        return top_12_names, top_specs, final_tags

# 3. 사용자 인터페이스(UI) 및 파일 처리
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

        st.success("✨ 데이터 분석이 완료되었습니다!")

        # 결과 섹션 1: 상품명 & 태그
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📝 1. 추천 상품명 (11~12단어)")
            st.code(" ".join(names), language=None)
            st.info("**분석 포인트:** 네이버 NLU 엔진이 선호하는 '의미 단위' 빈도수 상위 단어들을 띄어쓰기 형태로 조합했습니다.")

        with col2:
            st.subheader("🏷️ 2. 확장 검색인식태그 (10개)")
            st.warning(", ".join([f"#{t}" for t in tags]))
            st.info("**분석 포인트:** 상품명과 중복되지 않으면서 실제 검색 시 '인식'된 데이터만 선별하여 검색 그물을 넓혔습니다.")

        st.markdown("---")

        # 결과 섹션 2: 속성 키워드
        st.subheader("⚙️ 3. 권장 속성값 (필터 최적화용)")
        attr_cols = st.columns(4)
        for i, s in enumerate(specs):
            attr_cols[i % 4].button(s, key=f"btn_{i}", use_container_width=True)
        st.info("**분석 포인트:** 경쟁사들이 '스펙'란에 입력하여 노출 점수를 얻은 실제 속성 데이터입니다. 해당되는 항목을 속성란에 체크하세요.")

else:
    st.info("왼쪽 상단의 파일 업로더를 통해 CSV 파일을 업로드해주세요.")
