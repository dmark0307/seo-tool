import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
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
        """복합 명사 분리 및 수치값/브랜드 제거"""
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

    def reorder_for_readability(self, word_count_pairs):
        """가독성 그룹별 재배치"""
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

    def run_analysis(self, manual_input, total_target_count):
        manual_keywords = [w.strip() for w in manual_input.split() if len(w.strip()) > 0]
        
        # [1] 상품명 분석
        name_terms = []
        for name in self.df['상품명']:
            name_terms.extend(self.split_base_terms(name))
        
        name_freq = Counter(name_terms).most_common(50)
        auto_candidates = []
        for w, c in name_freq:
            if not any(manual_w in w or w in manual_w for manual_w in manual_keywords):
                auto_candidates.append((w, c))
        
        # [수정] 사용자가 설정한 총 키워드 수에서 수동 키워드 수를 뺌
        remain_count = max(0, total_target_count - len(manual_keywords))
        selected_auto_pairs = auto_candidates[:remain_count]
        readable_auto_pairs = self.reorder_for_readability(selected_auto_pairs)
        
        # [2] 속성 분석
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        # [3] 태그 분석
        tag_raw_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                parts = [t.strip() for t in str(tags).split(',')]
                tag_raw_list.extend([t for t in parts if not any(b in t for b in self.exclude_brands)])
        
        tag_freq = Counter(tag_raw_list).most_common(150)
        current_title_words = manual_keywords + [p[0] for p in readable_auto_pairs]
        
        valid_candidates = []
        for t, c in tag_freq:
            if not any(char.isdigit() for char in t) and not any(word in t for word in current_title_words):
                valid_candidates.append((t, c))

        final_tags = []
        used_roots = set()
        clusters = {
            '제과': ['제과', '제빵', '베이킹', '용품', '재료', '홈베이킹'],
            '맛': ['맛', '달달', '부드러운', '고소', '진한'],
            '영양': ['영양', '단백질', '건강', '몸에좋은'],
            '차': ['차', '음료', '커피', '티'],
            '간식': ['간식', '주전부리'],
            '용도': ['자판기', '식자재', '요리']
        }

        for t, c in valid_candidates:
            matched_root = None
            for root, keywords in clusters.items():
                if any(k in t for k in keywords):
                    matched_root = root
                    break
            if matched_root and matched_root not in used_roots:
                final_tags.append((t, c))
                used_roots.add(matched_root)

        for t, c in valid_candidates:
            if len(final_tags) >= 10: break
            if any(t == existing[0] for existing in final_tags): continue
            is_redundant = False
            for existing_t, _ in final_tags:
                if t in existing_t or existing_t in t:
                    is_redundant = True
                    break
            if not is_redundant:
                final_tags.append((t, c))
        
        final_tags = sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]
        
        return manual_keywords, readable_auto_pairs, spec_counts, final_tags

# 3. 사용자 인터페이스 (GUI)
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 전략 설정")
manual_input = st.sidebar.text_input(
    "실제 구매 유입 키워드 입력", 
    placeholder="예: 맛있는 속편한 국내산"
)

# [추가] 총 키워드 수 설정 입력란
total_kw_count = st.sidebar.number_input(
    "상품명 총 키워드 수 설정", 
    min_value=5, 
    max_value=25, 
    value=12,
    help="수동 입력 키워드를 포함한 상품명의 최종 단어 개수를 정합니다. 네이버는 보통 10~15개를 권장합니다."
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
        # [수정] total_kw_count를 분석 함수에 전달
        manual_keys, auto_keys_pairs, specs, tags = manager.run_analysis(manual_input, total_kw_count)

        st.success(f"✨ 총 {total_kw_count}개의 키워드 조합 분석이 완료되었습니다!")

        # 섹션 1: 상품명
        st.header("🏷️ 1. 전략적 상품명 조합")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("✅ 완성된 상품명")
            full_title = " ".join(manual_keys + [p[0] for p in auto_keys_pairs])
            st.code(full_title, language=None)
            st.caption(f"수동 키워드 {len(manual_keys)}개 + AI 자동 키워드 {len(auto_keys_pairs)}개")
        with col2:
            st.subheader("📊 자동 키워드 빈도")
            auto_df = pd.DataFrame(auto_keys_pairs, columns=['단어', '빈도(회)'])
            auto_df.index = auto_df.index + 1
            st.table(auto_df)

        st.markdown("---")

        # 섹션 2: 속성
        st.header("⚙️ 2. 필터 노출용 속성값")
        col3, col4 = st.columns([2, 1])
        with col3:
            for s, c in specs: st.button(f"{s}", key=f"attr_{s}", use_container_width=True)
        with col4:
            spec_df = pd.DataFrame(specs, columns=['속성값', '빈도'])
            spec_df.index = spec_df.index + 1
            st.table(spec_df)

        st.markdown("---")

        # 섹션 3: 태그
        st.header("🔍 3. 확장 검색 태그")
        col5, col6 = st.columns([2, 1])
        with col5:
            st.subheader("✅ 최적화 태그 10선")
            tag_display = ", ".join([f"#{t[0]}" for t in tags])
            st.warning(tag_display)
        with col6:
            st.subheader("📊 태그 인식 데이터")
            tag_df = pd.DataFrame(tags, columns=['태그명', '인식 횟수'])
            tag_df.index = tag_df.index + 1
            st.table(tag_df)

else:
    st.info("왼쪽 사이드바에서 파일을 업로드하고 설정을 확인해주세요.")
