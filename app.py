import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 (정밀 카운팅 마스터)")
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
        """상품명 내 단어를 원형 유지하며 정밀하게 분리"""
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        words = [w.strip() for w in text.split() if len(w.strip()) > 1]
        return [w for w in words if w not in self.exclude_brands and not any(c.isdigit() for c in w)]

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
        # [1] 고정 키워드 설정 (구매전환 + 추가)
        conversion_keywords = [w.strip() for w in conversion_input.split() if len(w.strip()) > 0]
        add_keywords = [w.strip() for w in add_input.split() if len(w.strip()) > 0]
        fixed_keywords = conversion_keywords + add_keywords
        
        # [2] 상품명 빈도 분석 (정밀)
        all_name_words = []
        for name in self.df['상품명']:
            all_name_words.extend(self.split_base_terms(name))
        
        name_counts = Counter(all_name_words)
        auto_candidates = [(w, c) for w, c in name_counts.most_common(100) if w not in fixed_keywords]
        
        remain_count = max(0, total_target_count - len(fixed_keywords))
        selected_auto_pairs = auto_candidates[:remain_count]
        readable_auto_pairs = self.reorder_for_readability(selected_auto_pairs)
        
        # [3] 속성 분석 (원형 보존)
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        # [4] 태그 분석 (빈도수 오류 해결 핵심 로직)
        tag_raw_list = []
        for tags_row in self.df['검색인식태그'].dropna():
            if tags_row != '-':
                # 쉼표로 정확히 분리 후 공백 제거하여 데이터 원형 보존
                raw_tags = [t.strip() for t in str(tags_row).split(',') if t.strip()]
                tag_raw_list.extend(raw_tags)
        
        # ★ 필터링 전 전체 카운팅 우선 원칙 (엑셀 찾기 결과와 일치시키는 핵심)
        tag_freq_map = Counter(tag_raw_list)
        
        # 현재 상품명에 쓰인 단어 집합 (완전 일치 체크용)
        current_title_words = set(fixed_keywords + [p[0] for p in readable_auto_pairs])
        
        valid_tags = []
        for tag, count in tag_freq_map.most_common(300):
            # 필터 1: 제외어 및 숫자 포함 단어 배제
            if any(b in tag for b in self.exclude_brands) or any(c.isdigit() for c in tag):
                continue
            # 필터 2: 상품명과 '완전히 똑같은' 태그만 제외 (부분 일치 중복 제거 금지)
            if tag in current_title_words:
                continue
            valid_tags.append((tag, count))

        # 최종 10선 선별 (유사 의미 그룹핑)
        final_tags = []
        clusters = {'제과': ['제과', '제빵', '베이킹'], '맛': ['맛', '달달', '고소'], '영양': ['영양', '단백질'], '용도': ['자판기', '식자재']}
        used_roots = set()

        for t, c in valid_tags:
            matched_root = None
            for root, keywords in clusters.items():
                if any(k in t for k in keywords):
                    matched_root = root; break
            if matched_root and matched_root not in used_roots:
                final_tags.append((t, c)); used_roots.add(matched_root)

        for t, c in valid_tags:
            if len(final_tags) >= 10: break
            if any(t == existing[0] for existing in final_tags): continue
            
            is_redundant = False
            for ex_t, _ in final_tags:
                if t == ex_t: # 완전 일치할 때만 중복으로 간주
                    is_redundant = True; break
            if not is_redundant: final_tags.append((t, c))
        
        final_tags = sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]
        
        return fixed_keywords, readable_auto_pairs, spec_counts, final_tags

# --- 사이드바 인터페이스 ---
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

    st.success(f"✨ 총 {total_kw_count}개 키워드 정밀 분석 완료!")

    # 섹션 1: 상품명
    st.header("🏷️ 1. 전략적 상품명 조합")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("✅ 완성된 상품명")
        full_title = " ".join(fixed_keys + [p[0] for p in auto_keys_pairs])
        st.code(full_title, language=None)
        st.info("**가독성 전략:** [구매전환 키워드] + [제품본질] + [제형] + [용도] + [속성] 순으로 자동 정렬")
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

    # 섹션 3: 태그 (빈도수 보정 완료)
    st.header("🔍 3. 확장 검색 태그 (정확한 사용빈도 측정)")
    col5, col6 = st.columns([2, 1])
    with col5:
        st.subheader("✅ 최적화 태그 10선")
        tag_display = ", ".join([f"#{t[0]}" for t in tags])
        st.warning(tag_display)
        st.info("**업데이트:** 상품명에 포함된 단어(예: '제과')가 있어도 태그명('제과제빵')과 완전히 일치하지 않으면 빈도수를 누락 없이 카운트합니다.")
    with col6:
        st.subheader("📊 태그 인식 데이터")
        tag_df = pd.DataFrame(tags, columns=['태그명', '사용 빈도수'])
        tag_df.index = tag_df.index + 1
        st.table(tag_df)
else:
    st.info("파일을 업로드하면 정밀 SEO 분석이 시작됩니다.")
