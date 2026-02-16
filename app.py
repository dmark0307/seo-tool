import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 (확장성 극대화 버전)")
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
        """상품명 정밀 분리 (수치 및 브랜드 제외)"""
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        words = [w.strip() for w in text.split() if len(w.strip()) > 1]
        return [w for w in words if w not in self.exclude_brands and not any(c.isdigit() for c in w)]

    def reorder_for_readability(self, word_count_pairs):
        """가독성 그룹별 재배치"""
        identity = ['전지', '분유', '우유', '탈지']
        form = ['분말', '가루', '스틱', '액상']
        usage = ['자판기', '업소용', '대용량', '식자재', '제과', '제빵', '베이킹']
        desc = ['진한', '고소한', '맛있는', '추억']

        def get_priority(pair):
            word = pair[0]
            if any(core in word for core in identity): return 1
            if any(core in word for core in form): return 2
            if any(core in word for core in usage): return 3
            if any(core in word for core in desc): return 4
            return 5
        return sorted(word_count_pairs, key=lambda x: get_priority(x))

    def run_analysis(self, conversion_input, add_input, total_target_count):
        # [1] 고정 키워드
        conversion_keywords = [w.strip() for w in conversion_input.split() if len(w.strip()) > 0]
        add_keywords = [w.strip() for w in add_input.split() if len(w.strip()) > 0]
        fixed_keywords = conversion_keywords + add_keywords
        
        # [2] 상품명 분석
        all_name_words = []
        for name in self.df['상품명']:
            all_name_words.extend(self.split_base_terms(name))
        
        name_counts = Counter(all_name_words)
        auto_candidates = [(w, c) for w, c in name_counts.most_common(100) if w not in fixed_keywords]
        
        remain_count = max(0, total_target_count - len(fixed_keywords))
        selected_auto_pairs = auto_candidates[:remain_count]
        readable_auto_pairs = self.reorder_for_readability(selected_auto_pairs)
        
        # [3] 속성 분석
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        # [4] 태그 분석 - ★ 조합 확장성 극대화 로직 ★
        tag_raw_list = []
        for tags_row in self.df['검색인식태그'].dropna():
            if tags_row != '-':
                raw_tags = [t.strip() for t in str(tags_row).split(',') if t.strip()]
                tag_raw_list.extend(raw_tags)
        
        # 정밀 카운팅 (필터링 전 원본 빈도)
        tag_freq_map = Counter(tag_raw_list)
        
        # 제목 단어 집합 (완전 일치 제외용)
        title_set = set(fixed_keywords + [p[0] for p in readable_auto_pairs])
        
        # 1차 필터링 (브랜드, 숫자, 제목 완전일치 제거)
        pre_filtered = []
        for tag, count in tag_freq_map.most_common(500):
            if any(b in tag for b in self.exclude_brands) or any(c.isdigit() for c in tag): continue
            if tag in title_set: continue
            pre_filtered.append((tag, count))

        # --- 중복 배제 및 카테고리 분산 알고리즘 ---
        final_tags = []
        
        # 의미 그룹 (이 그룹당 1개만 우선 선별하여 확장성 확보)
        clusters = {
            '제과제빵': ['제과', '제빵', '베이킹', '용품'],
            '풍미/맛': ['맛', '고소', '진한', '달달'],
            '용도': ['자판기', '식자재', '요리', '식당'],
            '타겟/영양': ['단백질', '영양', '간식', '어린이', '사무실'],
            '신뢰/특징': ['국내산', '천연', '무첨가', '수입']
        }
        used_clusters = set()

        # Step A: 카테고리별 최고 빈도 태그 1개씩 선점
        for tag, count in pre_filtered:
            for cluster_name, keywords in clusters.items():
                if any(k in tag for k in keywords) and cluster_name not in used_clusters:
                    final_tags.append((tag, count))
                    used_clusters.add(cluster_name)
                    break

        # Step B: 남은 자리를 빈도수 높은 순으로 채우되, '포함 관계' 중복 철저 배제
        for tag, count in pre_filtered:
            if len(final_tags) >= 10: break
            if any(tag == existing[0] for existing in final_tags): continue
            
            # 상호 포함 관계 검사 (예: '제과용'이 이미 뽑힌 '제과제빵재료'에 포함되는지 등)
            is_redundant = False
            for ex_tag, _ in final_tags:
                if tag in ex_tag or ex_tag in tag:
                    is_redundant = True
                    break
            
            if not is_redundant:
                final_tags.append((tag, count))
        
        # 최종 리스트를 빈도수 높은 순으로 정렬
        final_tags = sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]
        
        return fixed_keywords, readable_auto_pairs, spec_counts, final_tags

# --- 사이드바 ---
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 전략 설정")
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

    st.success(f"✅ 정밀 분석 완료! (총 {total_kw_count}개 키워드 타겟팅)")

    # 섹션 1: 상품명
    st.header("🏷️ 1. 전략적 상품명 조합")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("✅ 완성된 상품명")
        full_title = " ".join(fixed_keys + [p[0] for p in auto_keys_pairs])
        st.code(full_title, language=None)
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

    # 섹션 3: 태그 (확장성 극대화)
    st.header("🔍 3. 확장 검색 태그 (조합 확장성 극대화)")
    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        st.subheader("✅ 최적화 태그 10선")
        tag_display = ", ".join([f"#{t[0]}" for t in tags])
        st.warning(tag_display)
        st.info("""
        **확장성 로직 적용:**
        1. **정밀 카운팅:** 엑셀 원본과 동일하게 모든 발생 횟수를 누락 없이 집계합니다.
        2. **카테고리 분산:** '제과', '맛', '용도' 등 서로 다른 카테고리의 대표 태그를 우선 배치합니다.
        3. **중복 원천 차단:** 의미가 겹치거나 포함 관계에 있는 단어를 배제하여 유입 경로를 최대화했습니다.
        """)
    with col_t2:
        st.subheader("📊 태그 사용 빈도수")
        tag_df = pd.DataFrame(tags, columns=['태그명', '사용 빈도수'])
        tag_df.index = tag_df.index + 1
        st.table(tag_df)
else:
    st.info("파일을 업로드하면 정밀 SEO 분석이 시작됩니다.")
