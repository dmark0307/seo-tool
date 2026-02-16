import streamlit as st
import pandas as pd
import re
from collections import Counter
import io

# 1. 페이지 제목 및 레이아웃 설정
st.set_page_config(page_title="사내 SEO 분석 도구", layout="wide")
st.title("📊 전직원 공용 네이버 SEO 최적화 도구")
st.markdown("---")

# 2. 분석 핵심 로직 (SEOManager 클래스)
class SEOManager:
    def __init__(self, df):
        self.df = df
        # 지재권 이슈 방지를 위한 브랜드 제외 리스트
        self.exclude_brands = [
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ]

    def split_words(self, text):
        if pd.isna(text) or text == '-': return []
        # 특수문자 제거 및 띄어쓰기 기준 분리
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        words = text.split()
        return [w for w in words if len(w) > 1 and w not in self.exclude_brands and not w.isdigit()]

    def run_analysis(self):
        # 상품명 단어 빈도 분석
        all_words = []
        for name in self.df['상품명']:
            all_words.extend(self.split_words(name))
        
        # 상위 12개 핵심 텀(Term) 추출
        top_12_names = [w for w, c in Counter(all_words).most_common(12)]
        
        # 태그 분석 및 중복 제거
        tag_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                parts = [t.strip() for t in str(tags).split(',')]
                tag_list.extend([t for t in parts if not any(b in t for b in self.exclude_brands)])
        
        final_tags = []
        for t in [w for w, c in Counter(tag_list).most_common(50)]:
            if len(final_tags) >= 10: break
            # 상품명에 포함된 단어는 태그에서 제외 (확장성 극대화)
            if not any(word in t for word in top_12_names):
                final_tags.append(t)
        
        return top_12_names, final_tags

# 3. GUI 및 파일 처리 (여기가 에러 해결의 핵심입니다)
# ★ 변수 정의를 로직보다 먼저 수행합니다.
uploaded_file = st.file_uploader("네이버 쇼핑 분석 CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file:
    df = None
    # 인코딩 및 파일 포인터 방어 로직
    try:
        # 시도 1: cp949 (일반적인 엑셀 저장용)
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except Exception:
        uploaded_file.seek(0) # 첫 읽기 실패 시 포인터를 처음으로 되돌림
        try:
            # 시도 2: utf-8-sig (한글 포함 범용)
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        except Exception as e:
            st.error(f"파일을 읽는 중 에러가 발생했습니다: {e}")

    if df is not None:
        if df.empty:
            st.warning("업로드된 파일에 데이터가 없습니다.")
        else:
            # 분석 및 결과 출력
            manager = SEOManager(df)
            names, tags = manager.run_analysis()

            st.success("✅ 분석이 완료되었습니다!")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📝 추천 상품명 (11~12단어 조합)")
                st.code(" ".join(names), language=None)
                st.caption("💡 띄어쓰기 기준 NLU 최적화 조합입니다.")
            
            with col2:
                st.subheader("🏷️ 확장 검색인식태그 (10개)")
                st.info(", ".join([f"#{t}" for t in tags]))
                st.caption("💡 상품명과 중복되지 않는 효율적인 태그들입니다.")
else:
    st.info("사이드바 또는 상단 파일 업로더에 분석할 CSV 파일을 끌어다 놓으세요.")
