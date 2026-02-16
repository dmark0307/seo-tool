import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 매니저 (안정화 버전)")
st.markdown("---")

class SEOManager:
    def __init__(self, df, user_exclude_list):
        self.df = df
        # 브랜드 및 필터 키워드
        self.exclude_brands = set([
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ] + user_exclude_list)

    def normalize(self, text):
        """데이터 정규화: 보이지 않는 문자 및 공백 완벽 제거"""
        if pd.isna(text): return ""
        text = re.sub(r'[\x00-\x1F\x7F]', '', str(text)) # 제어 문자 제거
        return text.strip()

    def split_base_terms(self, text):
        """상품명 정밀 분리 (수치 및 브랜드 제외)"""
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        words = [w.strip() for w in text.split() if len(w.strip()) > 1]
        return [w for w in words if w not in self.exclude_brands and not any(c.isdigit() for c in w)]

    def reorder_for_readability(self, word_count_pairs):
        """가독성 그룹별 재배치 전략"""
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
        # [1] 고정 키워드 설정
        conv_keys = [self.normalize(w) for w in conversion_input.split() if w.strip()]
        add_keys = [self.normalize(w) for w in add_input.split() if w.strip()]
        fixed_keywords = conv_keys + add_keys
        
        # [2] 상품명 분석
        all_name_words = []
        for name in self.df['상품명']:
            all_name_words.extend(self.split_base_terms(name))
        
        name_counts = Counter(all_name_words)
        auto_candidates = [(w, c) for w, c in name_counts.most_common(100) if w not in fixed_keywords]
        
        remain_count = max(0, total_target_count - len(fixed_keywords))
        auto_pairs = auto_candidates[:remain_count]
        readable_auto = self.reorder_for_readability(auto_pairs)
        
        # [3] 속성 분석
        spec_list = []
        for spec in self.df['스펙'].dropna():
            parts = [p.strip() for p in str(spec).split('|')]
            spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        # [4] 태그 분석 - ★ 빈도수 오류 해결(13회) 및 확장성 로직 ★
        tag_raw_list = []
        for row in self.df['검색인식태그'].dropna():
            tags = [self.normalize(t) for t in str(row).split(',') if self.normalize(t)]
            tag_raw_list.extend(tags)
        
        # 1. 엑셀 원본 그대로의 빈도수 카운트 (통계용)
        tag_freq_map = Counter(tag_raw_list)
        
        # 2. 추천 필터링 (완전 일치만 제거하여 숫자 누락 방지)
        title_set = set(fixed_keywords + [p[0] for p in readable_auto])
        valid_tags = []
        for tag, count in tag_freq_map.most_common(500):
            if any(b in tag for b in self.exclude_brands) or any(c.isdigit() for c in tag): continue
            if tag in title_set: continue
            valid_tags.append((tag, count))

        # 3. 확장성 극대화 알고리즘
        final_tags = []
        clusters = {'제과':['제과','제빵','베이킹'], '맛':['맛','달달','고소'], '영양':['영양','단백질'], '용도':['자판기','식자재']}
        used_roots = set()

        for t, c in valid_tags:
            matched = None
            for root, keywords in clusters.items():
                if any(k in t for k in keywords): matched = root; break
            if matched and matched not in used_roots:
                final_tags.append((t, c)); used_roots.add(matched)

        for t, c in valid_tags:
            if len(final_tags) >= 10: break
            if any(t == ex[0] for ex in final_tags): continue
            if not any(t in ex[0] or ex[0] in t for ex in final_tags):
                final_tags.append((t, c))
        
        # 결과 반환
        return conv_keys, add_keys, readable_auto, spec_counts, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10], tag_freq_map.most_common(50)

def calculate_bytes(text):
    return len(text.encode('euc-kr', errors='replace'))

# 3. 사이드바 UI
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 전략 설정")
conversion_input = st.sidebar.text_input("구매전환 키워드", placeholder="예: 맛있는 속편한")
add_input = st.sidebar.text_input("추가할 키워드 (고정 배치)", placeholder="예: 국내산 당일발송")
exclude_input = st.sidebar.text_input("제외할 키워드 (분석 제외)", placeholder="예: 브랜드명")
total_kw_count = st.sidebar.number_input("상품명 총 키워드 수 설정", min_value=5, max_value=25, value=11)

user_exclude_list = [w.strip() for w in exclude_input.split() if w.strip()]

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df, user_exclude_list)
    conv, add, auto, specs, tags, raw_stats = manager.run_analysis(conversion_input, add_input, total_kw_count)

    st.success("✅ 복구가 완료되었습니다! 데이터 정밀 분석 결과입니다.")

    # 섹션 1: 상품명
    st.header("🏷️ 1. 전략적 상품명 조합")
    full_title = " ".join(conv + add + [p[0] for p in auto])
    title_len, kw_count = len(full_title), len(conv) + len(add) + len(auto)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("✅ 완성된 상품명")
        st.code(full_title, language=None)
        
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("총 키워드 수", f"{kw_count}개")
        m2.metric("총 글자 수", f"{title_len}자 / 50자", delta="🟢 정상" if title_len <= 50 else "🔴 초과", delta_color="normal" if title_len <= 50 else "inverse")
        m3.metric("총 바이트", f"{calculate_bytes(full_title)}B")
        st.info(f"**구성:** 구매전환({len(conv)}) + 추가({len(add)}) + 자동추천({len(auto)})")

    with col2:
        st.subheader("📊 키워드 사용 빈도수")
        st.table(pd.DataFrame(auto, columns=['단어', '빈도']).assign(index=range(1, len(auto)+1)).set_index('index'))

    st.markdown("---")

    # 섹션 2: 속성
    st.header("⚙️ 2. 필터 노출용 속성값")
    col3, col4 = st.columns([2, 1])
    with col3:
        for s, _ in specs: st.button(s, key=f"btn_{s}", use_container_width=True)
    with col4:
        st.table(pd.DataFrame(specs, columns=['속성값', '빈도']).assign(index=range(1, len(specs)+1)).set_index('index'))

    st.markdown("---")

    # 섹션 3: 태그 (확장성 극대화)
    st.header("🔍 3. 확장 검색 태그 (조합 확장성 극대화)")
    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        st.subheader("✅ 최적화 태그 10선")
        st.warning(", ".join([f"#{t[0]}" for t in tags]))
        st.info("**정밀 업데이트:** 엑셀 원본 빈도수를 100% 반영하며, 중복 없는 최적의 조합으로 선별되었습니다.")
    with col_t2:
        st.subheader("📊 태그 사용 빈도수 (원본)")
        st.table(pd.DataFrame(raw_stats[:20], columns=['태그명', '사용 빈도수']).assign(index=range(1, 21)).set_index('index'))
else:
    st.info("파일을 업로드하면 정밀 SEO 분석이 시작됩니다.")
