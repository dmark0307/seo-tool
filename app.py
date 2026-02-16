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
        """상품명 분석: 수치 및 브랜드 제외 로직"""
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
        # 1. 고정 키워드 리스트화
        conversion_keywords = [w.strip() for w in conversion_input.split() if len(w.strip()) > 0]
        add_keywords = [w.strip() for w in add_input.split() if len(w.strip()) > 0]
        fixed_keywords = conversion_keywords + add_keywords
        
        # 2. 상품명 빈도 분석
        name_terms = []
        for name in self.df['상품명']:
            name_terms.extend(self.split_base_terms(name))
        
        name_freq = Counter(name_terms).most_common(50)
        auto_candidates = []
        for w, c in name_freq:
            if not any(fixed_w == w for fixed_w in fixed_keywords): # 완전 일치만 체크
                auto_candidates.append((w, c))
        
        remain_count = max(0, total_target_count - len(fixed_keywords))
        selected_auto_pairs = auto_candidates[:remain_count]
        readable_auto_pairs = self.reorder_for_readability(selected_auto_pairs)
        
        # 3. 속성 분석
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        # 4. 태그 분석 - ★ 오류 해결 포인트 ★
        tag_raw_list = []
        for row in self.df['검색인식태그'].dropna():
            if row != '-':
                # 공백을 포함할 수 있으므로 strip()으로 정밀하게 분리
                parts = [t.strip() for t in str(row).split(',') if t.strip()]
                tag_raw_list.extend(parts)
        
        # [중요] 필터링 전에 "전체 원본 빈도수"를 먼저 계산하여 오차를 없앰
        tag_raw_counts = Counter(tag_raw_list)
        
        # 제목 및 수동 키워드 집합 (태그 제외용)
        current_title_words = set(fixed_keywords + [p[0] for p in readable_auto_pairs])
        
        valid_candidates = []
        for tag, count in tag_raw_counts.most_common(300):
            # 수치 제외 및 브랜드 제외
            if any(char.isdigit() for char in tag) or any(b in tag for b in self.exclude_brands):
                continue
            # 상품명 단어와 '완전 일치'할 때만 제외 (부분 일치 중복 제거 금지)
            if tag in current_title_words:
                continue
            valid_candidates.append((tag, count))

        # --- 확장성 극대화 알고리즘 ---
        final_tags = []
        used_roots = set()
        clusters = {
            '제과제빵': ['제과', '제빵', '베이킹'],
            '풍미/맛': ['맛', '달달', '고소', '진한'],
            '영양/특징': ['영양', '단백질', '국내산'],
            '용도': ['자판기', '식자재', '요리']
        }

        # Step A: 클러스터별 대표 주자 1명씩 우선 선발
        for t, c in valid_candidates:
            matched_root = None
            for root, keywords in clusters.items():
                if any(k in t for k in keywords):
                    matched_root = root; break
            if matched_root and matched_root not in used_roots:
                final_tags.append((t, c)); used_roots.add(matched_root)

        # Step B: 남은 자리를 빈도순으로 채우되, '완전 중복'만 배제
        for t, c in valid_candidates:
            if len(final_tags) >= 10: break
            if any(t == existing[0] for existing in final_tags): continue
            
            # 의미가 완전히 겹치는 경우(포함 관계)만 배제하여 확장성 확보
            is_redundant = False
            for ex_t, _ in final_tags:
                if t == ex_t: # 완전 일치할 때만 중복 간주
                    is_redundant = True; break
            if not is_redundant: final_tags.append((t, c))
        
        final_tags = sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]
        
        return fixed_keywords, readable_auto_pairs, spec_counts, final_tags

# 3. 사용자 인터페이스 (GUI)
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 전략 키워드 설정")
conversion_input = st.sidebar.text_input("구매전환 키워드", placeholder="예: 맛있는 속편한")
add_input = st.sidebar.text_input("추가할 키워드 (고정 배치)", placeholder="예: 국내산 당일발송")
exclude_input = st.sidebar.text_input("제외할 키워드 (분석 제외)", placeholder="예: 브랜드명")

total_kw_count = st.sidebar.number_input("상품명 총 키워드 수 설정", min_value=5, max_value=25, value=11)

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
        st.code(full_title, language=None)
        st.info("**가독성 전략:** [구매전환 키워드] + [제품본질] + [제형] + [용도] + [속성] 순 배치")
    with col2:
        st.subheader("📊 자동 키워드 사용 빈도")
        auto_df = pd.DataFrame(auto_keys_pairs, columns=['단어', '사용 빈도수'])
        auto_df.index = auto_df.index + 1
        st.table(auto_df)

    st.markdown("---")

    # 섹션 2: 속성
    st.header("⚙️ 2. 필터 노출용 속성값")
    col3, col4 = st.columns([2, 1])
    with col3:
        for s, c in specs: st.button(f"{s}", key=f"attr_{s}", use_container_width=True)
    with col4:
        spec_df = pd.DataFrame(specs, columns=['속성값', '사용 빈도수'])
        spec_df.index = spec_df.index + 1
        st.table(spec_df)

    st.markdown("---")

    # 섹션 3: 태그 (정밀 빈도 보정 및 확장성 강화)
    st.header("🔍 3. 확장 검색 태그 (정밀 카운팅 및 확장성 극대화)")
    col5, col6 = st.columns([2, 1])
    with col5:
        st.subheader("✅ 최적화 태그 10선")
        tag_display = ", ".join([f"#{t[0]}" for t in tags])
        st.warning(tag_display)
        st.info("**업데이트 노트:**\n- **정밀 빈도수:** '제과'가 상품명에 있다고 '제과제빵'을 쳐내지 않습니다. 엑셀 원본 그대로 13회를 정확히 반영합니다.\n- **확장성:** 비슷한 단어들 중 중복을 피하고, '맛', '특징', '용도' 등 다양한 유입 경로를 확보했습니다.")
    with col6:
        st.subheader("📊 태그 사용 빈도수")
        tag_df = pd.DataFrame(tags, columns=['태그명', '사용 빈도수'])
        tag_df.index = tag_df.index + 1
        st.table(tag_df)
else:
    st.info("왼쪽 사이드바에서 파일을 업로드하고 설정을 확인해주세요.")
