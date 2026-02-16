import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 제목 및 레이아웃
st.set_page_config(page_title="사내 SEO 분석 도구", layout="wide")
st.title("📊 전직원 공용 네이버 SEO 최적화 도구")
st.markdown("---")

# 2. 제외 단어 설정 (브랜드명 등)
EXCLUDE_WORDS = ['매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', '셀로몬', '희창유업']

# 3. 핵심 분석 함수
def analyze_seo(df):
    # NLU 기반 단어 쪼개기
    all_names = []
    for name in df['상품명']:
        clean_n = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(name))
        words = [w for w in clean_n.split() if len(w) > 1 and w not in EXCLUDE_WORDS and not w.isdigit()]
        all_names.extend(words)
    
    # 상위 12개 텀 추출 (nluterms 기준)
    top_names = [w for w, c in Counter(all_names).most_common(12)]
    
    # 태그 추출 (중복 제거 로직)
    all_tags = []
    for t_row in df['검색인식태그'].dropna():
        if t_row != '-':
            ts = [t.strip() for t in str(t_row).split(',') if t.strip() not in EXCLUDE_WORDS]
            all_tags.extend(ts)
    
    final_tags = []
    for t in [w for w, c in Counter(all_tags).most_common(50)]:
        if len(final_tags) >= 10: break
        if not any(word in t for word in top_names):
            final_tags.append(t)
            
    return top_names, final_tags

# 4. 파일 업로드 및 결과 표시
uploaded_file = st.file_uploader("분석할 CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
    
    names, tags = analyze_seo(df)
    
    st.subheader("✅ 추천 상품명 (11~12단축 조합)")
    st.code(" ".join(names), language=None)
    
    st.subheader("✅ 추천 태그 (중복 배제 10선)")
    st.info(", ".join([f"#{t}" for t in tags]))
