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
        self.exclude_brands = [
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ] + user_exclude_list

    def split_base_terms(self, text):
        """복합 명사 분리 및 불용어 제거"""
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
        conv_keys = [w.strip() for w in conversion_input.split() if len(w.strip()) > 0]
        add_keys = [w.strip() for w in add_input.split() if len(w.strip()) > 0]
        fixed_keywords = conv_keys + add_keys
        
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
        
        # 스펙 분석
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        # 태그 분석 로직
        tag_raw_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                parts = [t.strip() for t in str(tags).split(',')]
                tag_raw_list.extend([t for t in parts if not any(b in t for b in self.exclude_brands)])
        
        tag_freq = Counter(tag_raw_list).most_common(150)
        current_title_words = fixed_keywords + [p[0] for p in readable_auto_pairs]
        
        # 1차 필터링: 제목 중복 및 숫자 포함 단어 제거
        candidates = []
        for t, c in tag_freq:
            if not any(char.isdigit() for char in t) and not any(word in t for word in current_title_words):
                candidates.append((t, c))

        # [핵심 로직] 조합 확장성 극대화 선별 (Subsumption Logic)
        # 정보량이 더 많은(긴) 단어를 우선적으로 선별하여 검색 그물을 넓힘
        final_tags = []
        
        # 빈도순으로 정렬된 후보군을 다시 '길이'순으로 정렬하여 긴 단어 우선 검토
        # (단, 빈도가 너무 낮으면 안 되므로 상위 40개 중에서만 선별)
        top_candidates = candidates[:40]
        
        for i, (target_t, target_c) in enumerate(top_candidates):
            if len(final_tags) >= 10: break
            
            # 현재 단어가 다른 후보 단어에 포함되는지 확인 (예: '제과제빵'은 '제과제빵재료'에 포함됨)
            # 포함된다면, 더 큰 단어를 나중에 선택하기 위해 현재 단어는 스킵하거나 교체함
            is_subsumed = False
            for j, (compare_t, compare_c) in enumerate(top_candidates):
                if i != j and target_t in compare_t and target_t != compare_t:
                    # 더 큰 정보량을 가진 단어가 후보군에 존재함
                    is_subsumed = True
                    break
            
            if not is_subsumed:
                # 이미 뽑힌 단어와의 중복성 체크
                is_duplicate = False
                for existing_t, _ in final_tags:
                    if target_t == existing_t:
                        is_duplicate = True; break
                
                if not is_duplicate:
                    final_tags.append((target_t, target_c))

        # 만약 10개가 안 채워졌다면 빈도순으로 추가 보충
        selected_set = {t for t, c in final_tags}
        for t, c in candidates:
            if len(final_tags) >= 10: break
            if t not in selected_set:
                final_tags.append((t, c))
                selected_set.add(t)

        return fixed_keywords, readable_auto_pairs, spec_counts, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

def calculate_seo_metrics(text):
    """글자 수 및 바이트 계산"""
    char_count = len(text)
    try:
        byte_count = len(text.encode('euc-kr'))
    except:
        byte_count = len(text.encode('utf-8'))
    return char_count, byte_count

# 3. GUI 구성
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 전략 키워드 설정")
conversion_input = st.sidebar.text_input("구매전환 키워드", placeholder="예: 맛있는 속편한")
add_input = st.sidebar.text_input("추가할 키워드 (고정 배치)", placeholder="예: 국내산 당일발송")
exclude_input = st.sidebar.text_input("제외할 키워드 (분석 제외)", placeholder="예: 브랜드명")
total_kw_count = st.sidebar.number_input("상품명 목표 키워드 수", min_value=5, max_value=25, value=11)

user_exclude_list = [w.strip() for w in exclude_input.split() if len(w.strip()) > 0]

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df, user_exclude_list)
    fixed, auto, specs, tags = manager.run_analysis(conversion_input, add_input, total_kw_count)

    st.success("✨ SEO 최적화 분석이 완료되었습니다!")

    # 섹션 1: 상품명
    st.header("🏷️ 1. 전략적 상품명 조합")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("✅ 완성된 상품명")
        full_title = " ".join(fixed + [p[0] for p in auto])
        st.code(full_title, language=None)
        
        c_len, b_len = calculate_seo_metrics(full_title)
        if c_len <= 50:
            st.markdown(f"🟢 **정상**: {c_len}자 / {b_len} Byte")
        else:
            st.markdown(f"🔴 **주의**: {c_len}자 ({c_len-50}자 초과) / {b_len} Byte")
            st.warning("상품명이 50자를 초과하면 검색 결과에서 생략될 수 있습니다.")
            
        st.info("**가독성 전략:** 구매전환 → 제품본질 → 제형 → 용도 → 속성 순 정렬")

    with col2:
        st.subheader("📊 키워드 빈도 데이터")
        auto_df = pd.DataFrame(auto, columns=['단어', '빈도'])
        auto_df.index += 1
        st.table(auto_df)

    st.markdown("---")

    # 섹션 2: 속성
    st.header("⚙️ 2. 필터 노출용 속성값")
    col3, col4 = st.columns([2, 1])
    with col3:
        for s, _ in specs: st.button(s, key=f"attr_{s}", use_container_width=True)
    with col4:
        st.table(pd.DataFrame(specs, columns=['속성값', '빈도']).set_index(pd.Index(range(1, len(specs)+1))))

    st.markdown("---")

    # 섹션 3: 태그 (확장성 극대화 업데이트)
    st.header("🔍 3. 확장 검색 태그 (조합 효율 극대화)")
    col5, col6 = st.columns([2, 1])
    with col5:
        st.subheader("✅ 최적화 태그 10선")
        tag_display = ", ".join([f"#{t[0]}" for t in tags])
        st.success(tag_display)
        st.caption("※ '제과제빵'과 '제과제빵재료' 중 정보량이 더 많은 확장 단어를 우선 선택하여 노출 기회를 극대화했습니다.")
    with col6:
        st.subheader("📊 태그 사용 빈도수")
        tag_df = pd.DataFrame(tags, columns=['태그명', '사용 빈도수'])
        tag_df.index += 1
        st.table(tag_df)
else:
    st.info("왼쪽 사이드바에서 파일을 업로드하고 분석 설정을 확인해주세요.")
