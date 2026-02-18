import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 (안정화 버전 2.1)")
st.markdown("---")

class SEOManager:
    def __init__(self, df, user_exclude_list):
        self.df = df
        self.exclude_brands = set([
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ] + user_exclude_list)

    def normalize(self, text):
        if pd.isna(text): return ""
        text = re.sub(r'[\x00-\x1F\x7F]', '', str(text))
        return text.strip()

    def split_base_terms(self, text):
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        words = [w.strip() for w in text.split() if len(w.strip()) > 1]
        return [w for w in words if w not in self.exclude_brands and not any(c.isdigit() for c in w)]

    def reorder_for_readability(self, word_count_pairs):
        identity, form, usage, desc = ['전지', '분유', '우유', '탈지'], ['분말', '가루', '스틱', '액상'], ['자판기', '업소용', '대용량', '식자재', '제과', '제빵'], ['진한', '고소한', '맛있는', '추억']
        def get_priority(pair):
            word = pair[0]
            if any(c in word for c in identity): return 1
            if any(c in word for c in form): return 2
            if any(c in word for c in usage): return 3
            if any(c in word for c in desc): return 4
            return 5
        return sorted(word_count_pairs, key=lambda x: get_priority(x))

    def run_analysis(self, conv_input, add_input, total_count):
        # [1] 고정 키워드
        conv_keys = [self.normalize(w) for w in conv_input.split() if w.strip()]
        add_keys = [self.normalize(w) for w in add_input.split() if w.strip()]
        fixed_keywords = conv_keys + add_keys
        
        # [2] 상품명 분석
        all_name_words = []
        for name in self.df['상품명']:
            all_name_words.extend(self.split_base_terms(name))
        name_counts = Counter(all_name_words)
        auto_pairs = [(w, c) for w, c in name_counts.most_common(100) if w not in fixed_keywords]
        readable_auto = self.reorder_for_readability(auto_pairs[:max(0, total_count - len(fixed_keywords))])
        
        # [3] 스펙 분석 (4번째 리턴값용)
        spec_list = []
        for spec in self.df['스펙'].dropna():
            parts = [p.strip() for p in str(spec).split('|')]
            spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        # [4] 태그 분석 (확장성 극대화)
        tag_raw_list = []
        for row in self.df['검색인식태그'].dropna():
            tags = [self.normalize(t) for t in str(row).split(',') if self.normalize(t)]
            tag_raw_list.extend([t for t in tags if not any(b in t for b in self.exclude_brands)])
        
        tag_freq_map = Counter(tag_raw_list)
        title_set = set(fixed_keywords + [p[0] for p in readable_auto])
        candidates = [(t, c) for t, c in tag_freq_map.most_common(300) if t not in title_set and not any(char.isdigit() for char in t)]

        final_tags = []
        used_prefixes = set()

        for t, c in candidates:
            if len(final_tags) >= 10: break
            prefix = t[:3] if len(t) > 3 else t[:2]
            
            is_redundant = False
            for ex_t, _ in final_tags:
                # 수식어 중복 배제 (추억의맛 vs 추억의간식)
                if prefix in ex_t or any(ex_t[:3] in t for ex_t, _ in final_tags if len(ex_t) > 2):
                    is_redundant = True; break
                # 포함 관계 체크 (긴 단어 보존)
                if t in ex_t: is_redundant = True; break
            
            if not is_redundant:
                final_tags.append((t, c))
                used_prefixes.add(prefix)

        for t, c in candidates:
            if len(final_tags) >= 10: break
            if not any(t == ex[0] for ex in final_tags):
                final_tags.append((t, c))
        
        # ★ 총 6개의 값을 리턴합니다 ★
        return conv_keys, add_keys, readable_auto, spec_counts, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10], tag_freq_map.most_common(50)

def calculate_bytes(text):
    return len(text.encode('euc-kr', errors='replace'))

# 3. 사이드바 UI
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 전략 설정")
conversion_input = st.sidebar.text_input("구매전환 키워드")
add_input = st.sidebar.text_input("추가할 키워드")
total_kw_count = st.sidebar.number_input("상품명 총 키워드 수", min_value=5, max_value=25, value=11)

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df, [])
    # ★ 받는 쪽에서도 6개 변수를 정확히 지정했습니다 ★
    conv, add, auto, specs, tags, raw_stats = manager.run_analysis(conversion_input, add_input, total_kw_count)

    st.success("✨ 오류가 해결되었습니다! 분석 결과입니다.")

    # 1. 상품명 섹션
    st.header("🏷️ 1. 전략적 상품명 조합")
    full_title = " ".join(conv + add + [p[0] for p in auto])
    col1, col2 = st.columns([2, 1])
    with col1:
        st.code(full_title, language=None)
        m1, m2, m3 = st.columns(3)
        m1.metric("총 키워드", f"{len(conv)+len(add)+len(auto)}개")
        m2.metric("글자 수", f"{len(full_title)}자", delta="🟢 정상" if len(full_title) <= 50 else "🔴 초과", delta_color="normal" if len(full_title) <= 50 else "inverse")
        m3.metric("바이트", f"{calculate_bytes(full_title)}B")
    with col2:
        st.subheader("📊 자동 키워드 빈도")
        st.table(pd.DataFrame(auto, columns=['단어', '빈도']).assign(No=range(1, len(auto)+1)).set_index('No'))

    st.markdown("---")
    # 2. 속성 섹션 (specs 활용)
    st.header("⚙️ 2. 필터 노출용 속성값")
    col3, col4 = st.columns([2, 1])
    with col3:
        for s, _ in specs: st.button(s, key=f"btn_{s}", use_container_width=True)
    with col4:
        st.table(pd.DataFrame(specs, columns=['속성값', '빈도']).assign(No=range(1, len(specs)+1)).set_index('No'))

    st.markdown("---")
    # 3. 태그 섹션
    st.header("🔍 3. 확장 검색 태그 (조합 확장성 극대화)")
    t_col1, t_col2 = st.columns([2, 1])
    with t_col1:
        st.warning(", ".join([f"#{t[0]}" for t in tags]))
        st.info("💡 **수식어 필터링:** '#추억의맛'이 있으면 '#추억의간식'은 자동으로 제외하여 유입 경로를 넓혔습니다.")
    with t_col2:
        st.table(pd.DataFrame(raw_stats[:20], columns=['태그명', '사용 빈도수']).assign(No=range(1, 21)).set_index('No'))
