import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 (데이터 정합성 완벽 보정)")
st.markdown("---")

class SEOManager:
    def __init__(self, df, user_exclude_list):
        self.df = df
        self.exclude_brands = [
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ] + user_exclude_list

    def split_base_terms(self, text):
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        words = [w.strip() for w in text.split() if len(w.strip()) > 1]
        return [w for w in words if w not in self.exclude_brands and not any(c.isdigit() for c in w)]

    def reorder_for_readability(self, word_count_pairs):
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
        # 1. 고정 키워드
        conv_keys = [w.strip() for w in conversion_input.split() if w.strip()]
        add_keys = [w.strip() for w in add_input.split() if w.strip()]
        fixed_keywords = conv_keys + add_keys
        
        # 2. 상품명 분석
        all_name_words = []
        for name in self.df['상품명']:
            all_name_words.extend(self.split_base_terms(name))
        
        name_counts = Counter(all_name_words)
        auto_candidates = [(w, c) for w, c in name_counts.most_common(100) if w not in fixed_keywords]
        
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

        # 4. 태그 분석 (핵심 수정 구간)
        tag_raw_list = []
        for row in self.df['검색인식태그'].dropna():
            if row != '-':
                # 콤마로 분리, 앞뒤 공백 제거 (데이터 정규화)
                tags = [t.strip() for t in str(row).split(',') if t.strip()]
                tag_raw_list.extend(tags)
        
        # [A] 통계용: 필터링 없는 완전한 원본 빈도수 (Data Table용)
        raw_tag_counts = Counter(tag_raw_list).most_common(50) 
        
        # [B] 추천용: SEO 로직 적용 (Recommendation Box용)
        current_title_set = set(fixed_keywords + [p[0] for p in readable_auto_pairs])
        valid_candidates = []
        
        # 추천 후보 선정 시에는 필터링 적용
        for t, c in Counter(tag_raw_list).most_common(300):
            if any(b in t for b in self.exclude_brands) or any(char.isdigit() for char in t): continue
            if t in current_title_set: continue  # 제목에 있으면 추천에서는 제외 (하지만 통계표에는 남음)
            valid_candidates.append((t, c))

        # 조합 확장성 로직
        final_tags = []
        clusters = {'제과':['제과','제빵','베이킹'], '맛':['맛','달달','고소'], '영양':['영양','단백질'], '용도':['자판기','식자재']}
        used_roots = set()

        for t, c in valid_candidates:
            matched = None
            for root, keywords in clusters.items():
                if any(k in t for k in keywords): matched = root; break
            if matched and matched not in used_roots:
                final_tags.append((t, c)); used_roots.add(matched)

        for t, c in valid_candidates:
            if len(final_tags) >= 10: break
            if any(t == existing[0] for existing in final_tags): continue
            is_redundant = False
            for ex_t, _ in final_tags:
                if t == ex_t: is_redundant = True; break
            if not is_redundant: final_tags.append((t, c))
        
        # 반환값: (고정키워드, 자동키워드, 스펙, 추천태그10선, ★원본전체태그통계★)
        return fixed_keywords, readable_auto_pairs, spec_counts, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10], raw_tag_counts

# --- GUI ---
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
    # run_analysis에서 raw_tag_counts를 추가로 받음
    fixed_keys, auto_keys, specs, recommended_tags, raw_tag_stats = manager.run_analysis(conversion_input, add_input, total_kw_count)

    st.success(f"✨ 총 {total_kw_count}개 키워드 정밀 분석 완료!")

    # 섹션 1: 상품명
    st.header("🏷️ 1. 전략적 상품명 조합")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("✅ 완성된 상품명")
        full_title = " ".join(fixed_keys + [p[0] for p in auto_keys])
        st.code(full_title, language=None)
    with col2:
        st.subheader("📊 자동 키워드 빈도")
        name_df = pd.DataFrame(auto_keys, columns=['단어', '빈도(회)'])
        name_df.index = name_df.index + 1
        st.table(name_df)

    st.markdown("---")

    # 섹션 2: 속성
    st.header("⚙️ 2. 필터 노출용 속성값")
    col3, col4 = st.columns([2, 1])
    with col3:
        for s, _ in specs: st.button(s, key=f"attr_{s}", use_container_width=True)
    with col4:
        spec_df = pd.DataFrame(specs, columns=['속성값', '빈도'])
        spec_df.index = spec_df.index + 1
        st.table(spec_df)

    st.markdown("---")

    # 섹션 3: 태그 (여기가 핵심!)
    st.header("🔍 3. 확장 검색 태그 (정밀 카운팅)")
    col5, col6 = st.columns([2, 1])
    with col5:
        st.subheader("✅ 최적화 태그 10선 (추천)")
        tag_display = ", ".join([f"#{t[0]}" for t in recommended_tags])
        st.warning(tag_display)
        st.info("**로직 적용:** 중복 제거 및 확장성을 고려하여 AI가 선별한 최적의 조합입니다.")
        
    with col6:
        # ★ 수정됨: 추천 태그가 아닌 '원본 데이터 통계'를 그대로 출력
        st.subheader("📊 태그 원본 사용빈도 (TOP 20)")
        # raw_tag_stats는 리스트 형태이므로 그대로 DataFrame 변환
        raw_df = pd.DataFrame(raw_tag_stats[:20], columns=['태그명', '실제 사용빈도'])
        raw_df.index = raw_df.index + 1
        st.table(raw_df)
else:
    st.info("파일을 업로드하면 정밀 SEO 분석이 시작됩니다.")
