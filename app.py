import streamlit as st
import pandas as pd
import re
from collections import Counter
import io

# 1. 페이지 설정
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 (Pro 버전)")
st.markdown("---")

# 2. 전문 SEO 분석 로직 클래스
class SEOManager:
    def __init__(self, df, user_exclude_list):
        self.df = df
        # 브랜드 및 제외 키워드 통합
        self.exclude_brands = set([
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ] + user_exclude_list)

        # NLU 분석을 위한 형태소 분리 기준
        self.sub_splits = ['자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', '업소용', '대용량']

    def normalize_text(self, text):
        """텍스트 정규화: 특수문자 제거 및 공백 정리"""
        if pd.isna(text): return ""
        # 제어 문자 제거 및 한글/영문/숫자만 남기기
        text = re.sub(r'[\x00-\x1F\x7F]', '', str(text))
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', text)
        return text.strip()

    def split_base_terms(self, text):
        """상품명 분석: 수치/브랜드/불용어 제거 후 유효 키워드 추출"""
        text = self.normalize_text(text)
        raw_words = text.split()
        terms = []
        
        for word in raw_words:
            if word in self.exclude_brands or any(char.isdigit() for char in word):
                continue
            
            found_sub = False
            for sub in self.sub_splits:
                if sub in word and word != sub:
                    terms.append(sub)
                    rem = word.replace(sub, '').strip()
                    if len(rem) > 1 and not any(char.isdigit() for char in rem) and rem not in self.exclude_brands:
                        terms.append(rem)
                    found_sub = True
                    break
            if not found_sub and len(word) > 1:
                terms.append(word)
        return terms

    def reorder_for_readability(self, word_count_pairs):
        """상품명 가독성 배치 전략"""
        identity = ['전지', '분유', '우유', '탈지', '전지밀']
        form = ['분말', '가루', '스틱', '액상']
        usage = ['자판기', '업소용', '대용량', '식자재', '제과', '제빵', '베이킹']
        desc = ['진한', '고소한', '맛있는', '추억', '추천', '속편한']

        def get_priority(pair):
            word = pair[0]
            if any(core in word for core in identity): return 1
            if any(core in word for core in form): return 2
            if any(core in word for core in usage): return 3
            if any(core in word for core in desc): return 4
            return 5
        return sorted(word_count_pairs, key=lambda x: get_priority(x))

    def run_analysis(self, conversion_input, add_input, total_target_count):
        # [1] 고정 키워드 처리
        conv_keys = [w.strip() for w in conversion_input.split() if w.strip()]
        add_keys = [w.strip() for w in add_input.split() if w.strip()]
        fixed_keywords = conv_keys + add_keys
        
        # [2] 상품명 자동 추출 (Vectorized-like processing)
        all_name_words = []
        # apply를 사용하여 데이터프레임 처리 속도 최적화
        processed_names = self.df['상품명'].apply(self.split_base_terms)
        for words in processed_names:
            all_name_words.extend(words)
            
        name_counts = Counter(all_name_words)
        # 고정 키워드와 '완전 일치'하는 단어만 제외
        auto_candidates = [(w, c) for w, c in name_counts.most_common(100) if w not in fixed_keywords]
        
        remain_count = max(0, total_target_count - len(fixed_keywords))
        selected_auto_pairs = auto_candidates[:remain_count]
        readable_auto_pairs = self.reorder_for_readability(selected_auto_pairs)
        
        # [3] 속성 분석
        spec_list = []
        spec_series = self.df['스펙'].dropna().astype(str)
        for spec in spec_series:
            if spec != '-':
                parts = [p.strip() for p in spec.split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        # [4] 태그 분석 (정밀 카운팅 + 확장 추천)
        tag_series = self.df['검색인식태그'].dropna().astype(str)
        
        # A. 원본 데이터 정밀 카운팅 (통계용)
        raw_tags_all = []
        for row in tag_series:
            if row != '-':
                # 공백/특수문자 제거 후 순수 텍스트만 추출
                tags = [t.strip() for t in row.split(',') if t.strip()]
                raw_tags_all.extend(tags)
        
        raw_tag_stats = Counter(raw_tags_all).most_common(50) # 엑셀 원본 통계

        # B. 추천 알고리즘 (추천용)
        # 제목에 포함된 단어 집합 (완전 일치 비교용)
        title_set = set(fixed_keywords + [p[0] for p in readable_auto_pairs])
        
        valid_candidates = []
        for t, c in Counter(raw_tags_all).most_common(300):
            # 브랜드/숫자 필터링
            if any(b in t for b in self.exclude_brands) or any(char.isdigit() for char in t):
                continue
            # 제목에 이미 있는 단어는 '추천'에서만 제외 (통계에는 남음)
            if t in title_set:
                continue
            valid_candidates.append((t, c))

        # C. 조합 확장성 로직 (클러스터링)
        final_tags = []
        clusters = {
            '제과': ['제과', '제빵', '베이킹'], 
            '맛': ['맛', '달달', '고소', '풍미'], 
            '영양': ['영양', '단백질', '건강'], 
            '용도': ['자판기', '식자재', '요리']
        }
        used_roots = set()

        # C-1. 카테고리별 대표 태그 우선 선별
        for t, c in valid_candidates:
            matched = None
            for root, keywords in clusters.items():
                if any(k in t for k in keywords):
                    matched = root; break
            if matched and matched not in used_roots:
                final_tags.append((t, c)); used_roots.add(matched)

        # C-2. 나머지 빈자리 채우기 (포함 관계 중복 제거)
        for t, c in valid_candidates:
            if len(final_tags) >= 10: break
            if any(t == existing[0] for existing in final_tags): continue
            
            is_redundant = False
            for ex_t, _ in final_tags:
                if t in ex_t or ex_t in t: # 포함 관계 체크
                    is_redundant = True; break
            if not is_redundant: final_tags.append((t, c))
            
        final_recommendation = sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

        return fixed_keywords, readable_auto_pairs, spec_counts, final_recommendation, raw_tag_stats

    def create_excel_download(self, fixed_keys, auto_keys, specs, tags, raw_stats):
        """결과를 엑셀 파일로 변환"""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # 요약 시트
            summary_data = {
                '구분': ['완성된 상품명', '추천 태그(10선)'],
                '내용': [
                    " ".join(fixed_keys + [p[0] for p in auto_keys]),
                    ", ".join([f"#{t[0]}" for t in tags])
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='최적화_요약', index=False)
            
            # 상세 데이터 시트
            pd.DataFrame(auto_keys, columns=['키워드', '빈도']).to_excel(writer, sheet_name='상품명_키워드', index=False)
            pd.DataFrame(specs, columns=['속성', '빈도']).to_excel(writer, sheet_name='속성_분석', index=False)
            pd.DataFrame(raw_stats, columns=['태그명', '실제사용빈도']).to_excel(writer, sheet_name='전체_태그_통계', index=False)
            
        return output.getvalue()

# 3. GUI 구성
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 전략 키워드 설정")
conversion_input = st.sidebar.text_input("구매전환 키워드", placeholder="예: 맛있는 속편한")
add_input = st.sidebar.text_input("추가할 키워드 (고정 배치)", placeholder="예: 국내산 당일발송")
exclude_input = st.sidebar.text_input("제외할 키워드 (분석 제외)", placeholder="예: 브랜드명")
total_kw_count = st.sidebar.number_input("상품명 총 키워드 수", min_value=5, max_value=25, value=11)

user_exclude_list = [w.strip() for w in exclude_input.split() if len(w.strip()) > 0]

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df, user_exclude_list)
    fixed, auto, specs, rec_tags, raw_stats = manager.run_analysis(conversion_input, add_input, total_kw_count)

    st.success(f"✨ 분석 완료! (총 {total_kw_count}개 키워드 조합)")

    # 엑셀 다운로드 버튼
    excel_data = manager.create_excel_download(fixed, auto, specs, rec_tags, raw_stats)
    st.download_button(
        label="📥 분석 결과 엑셀 다운로드",
        data=excel_data,
        file_name="SEO_분석결과.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # 섹션 1: 상품명
    st.header("🏷️ 1. 전략적 상품명 조합")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("✅ 완성된 상품명")
        full_title = " ".join(fixed + [p[0] for p in auto])
        st.code(full_title, language=None)
        st.info("**가독성 전략:** [구매전환] + [추가] + [본질] + [제형] + [용도] + [속성]")
    with col2:
        st.subheader("📊 키워드 빈도")
        df_auto = pd.DataFrame(auto, columns=['단어', '빈도'])
        df_auto.index += 1
        st.table(df_auto)

    st.markdown("---")

    # 섹션 2: 속성
    st.header("⚙️ 2. 필터 노출용 속성값")
    col3, col4 = st.columns([2, 1])
    with col3:
        for s, _ in specs: st.button(s, key=s, use_container_width=True)
    with col4:
        df_spec = pd.DataFrame(specs, columns=['속성값', '빈도'])
        df_spec.index += 1
        st.table(df_spec)

    st.markdown("---")

    # 섹션 3: 태그 (정밀성 + 확장성)
    st.header("🔍 3. 확장 검색 태그")
    col5, col6 = st.columns([2, 1])
    with col5:
        st.subheader("✅ 최적화 태그 10선 (추천)")
        st.warning(", ".join([f"#{t[0]}" for t in rec_tags]))
        st.info("**최적화:** 중복 의미 배제 및 카테고리 확장 적용")
    with col6:
        st.subheader("📊 원본 사용 빈도 (Top 20)")
        df_raw = pd.DataFrame(raw_stats[:20], columns=['태그명', '실제 빈도'])
        df_raw.index += 1
        st.table(df_raw)

else:
    st.info("파일을 업로드하면 분석이 시작됩니다.")
