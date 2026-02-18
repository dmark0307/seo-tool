import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 매니저")
st.markdown("---")

# 2. 전문 SEO 분석 로직 클래스
class SEOManager:
    def __init__(self, df, user_exclude_list):
        self.df = df
        # 기본 브랜드 제외 리스트 + 사용자 입력 제외 키워드 통합
        self.exclude_brands = [
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ] + user_exclude_list

    def split_base_terms(self, text):
        """복합 명사 분리 및 수치값/브랜드/제외어 제거"""
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
                    if len(rem) > 1 and not any(char.isdigit() for char in rem) and rem not in self.exclude_brands:
                        terms.append(rem)
                    found_sub = True
                    break
            if not found_sub and len(word) > 1:
                terms.append(word)
        return terms

    def reorder_for_readability(self, word_count_pairs):
        """가독성 그룹별 재배치 (본질->제형->용도->속성)"""
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
        conversion_keywords = [w.strip() for w in conversion_input.split() if len(w.strip()) > 0]
        add_keywords = [w.strip() for w in add_input.split() if len(w.strip()) > 0]
        fixed_keywords = conversion_keywords + add_keywords
        
        name_terms = []
        for name in self.df['상품명']:
            name_terms.extend(self.split_base_terms(name))
        
        name_freq = Counter(name_terms).most_common(50)
        auto_candidates = []
        for w, c in name_freq:
            if not any(fixed_w in w or w in fixed_w for fixed_w in fixed_keywords):
                auto_candidates.append((w, c))
        
        remain_count = max(0, total_target_count - len(fixed_keywords))
        selected_auto_pairs = auto_candidates[:remain_count]
        readable_auto_pairs = self.reorder_for_readability(selected_auto_pairs)
        
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        tag_raw_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                parts = [t.strip() for t in str(tags).split(',')]
                tag_raw_list.extend([t for t in parts if not any(b in t for b in self.exclude_brands)])
        
        # 태그 빈도수 계산
        tag_freq = Counter(tag_raw_list).most_common(150)
        current_title_words = fixed_keywords + [p[0] for p in readable_auto_pairs]
        
        # 상품명에 포함된 단어만 제외 (포함 관계 제거)
        valid_candidates = []
        for t, c in tag_freq:
            if not any(char.isdigit() for char in t) and not any(word in t for word in current_title_words):
                valid_candidates.append((t, c))

        final_tags = []
        
        # [수정됨] 중복 필터링 로직: 100% 일치할 때만 중복 처리
        # '제과'가 있어도 '제과제빵'은 살아남음
        for t, c in valid_candidates:
            if len(final_tags) >= 10: break
            
            # 이미 선정된 태그 목록에 정확히 같은 단어가 있는지 확인
            is_exact_duplicate = False
            for existing_t, _ in final_tags:
                if t == existing_t:  # 정확히 같을 때만 중복
                    is_exact_duplicate = True
                    break
            
            if not is_exact_duplicate:
                final_tags.append((t, c))
        
        # 빈도순 정렬 (이미 되어있으나 확실하게)
        final_tags = sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]
        
        return fixed_keywords, readable_auto_pairs, spec_counts, final_tags

def check_length(text):
    """상품명 길이 및 바이트 계산 (네이버 기준: 한글 2byte, 영문 1byte)"""
    char_len = len(text)
    try:
        byte_len = len(text.encode('euc-kr'))
    except:
        byte_len = len(text.encode('utf-8')) # fallback
    
    return char_len, byte_len

# 3. 사용자 인터페이스 (GUI)
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 전략 키워드 설정")
conversion_input = st.sidebar.text_input("구매전환 키워드", placeholder="예: 맛있는 속편한")
add_input = st.sidebar.text_input("추가할 키워드 (고정 배치)", placeholder="예: 국내산 당일발송")
exclude_input = st.sidebar.text_input("제외할 키워드 (분석 제외)", placeholder="예: 브랜드명")

total_kw_count = st.sidebar.number_input(
    "상품명 총 키워드 수 설정", 
    min_value=5, 
    max_value=25, 
    value=11
)

user_exclude_list = [w.strip() for w in exclude_input.split() if len(w.strip()) > 0]

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df, user_exclude_list)
    fixed_keys, auto_keys_pairs, specs, tags = manager.run_analysis(conversion_input, add_input, total_kw_count)

    st.success(f"✨ 총 {total_kw_count}개 키워드 타겟팅 분석이 완료되었습니다!")

    # 섹션 1: 상품명
    st.header("🏷️ 1. 전략적 상품명 조합")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("✅ 완성된 상품명")
        full_title = " ".join(fixed_keys + [p[0] for p in auto_keys_pairs])
        
        # [추가됨] 길이 검증 로직
        c_len, b_len = check_length(full_title)
        
        # 50자 기준 검증 (네이버 권장 50자 이내)
        if c_len <= 50:
            st.code(full_title, language=None)
            st.markdown(f"🟢 **정상 (50자 이내)**: {c_len}자 / {b_len} Byte")
        else:
            st.code(full_title, language=None)
            st.markdown(f"🔴 **주의 (50자 초과)**: {c_len}자 ({c_len - 50}자 초과) / {b_len} Byte")
            st.warning("⚠️ 상품명이 너무 깁니다. 키워드 개수를 줄이거나 불필요한 단어를 삭제하세요.")

        st.info("**가독성 전략:** [구매전환 키워드] + [제품본질] + [제형] + [용도] + [속성] 순으로 자동 정렬")
        
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
        st.success(tag_display)
        st.caption("※ '제과'가 포함되어 있어도 '제과제빵'은 삭제되지 않습니다 (100% 일치 시에만 중복 처리)")
    with col6:
        st.subheader("📊 태그 사용 빈도수")
        tag_df = pd.DataFrame(tags, columns=['태그명', '사용 빈도수'])
        tag_df.index = tag_df.index + 1
        st.table(tag_df)
else:
    st.info("왼쪽 사이드바에서 파일을 업로드하고 설정을 확인해주세요.")
