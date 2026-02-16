import streamlit as st
import pandas as pd
import re
from collections import Counter
import io

# 1. 페이지 설정
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 매니저")
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
        conv_keys = [w.strip() for w in conversion_input.split() if w.strip()]
        add_keys = [w.strip() for w in add_input.split() if w.strip()]
        fixed_keywords = conv_keys + add_keys
        
        name_terms = []
        for name in self.df['상품명']:
            name_terms.extend(self.split_base_terms(name))
        
        name_freq = Counter(name_terms).most_common(50)
        auto_candidates = [(w, c) for w, c in name_freq if w not in fixed_keywords]
        
        remain_count = max(0, total_target_count - len(fixed_keywords))
        auto_pairs = auto_candidates[:remain_count]
        readable_auto = self.reorder_for_readability(auto_pairs)
        
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        tag_raw_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                parts = [t.strip() for t in str(tags).split(',') if t.strip()]
                tag_raw_list.extend(parts)
        
        tag_freq_map = Counter(tag_raw_list)
        title_set = set(fixed_keywords + [p[0] for p in readable_auto])
        valid_tags = [(t, c) for t, c in tag_freq_map.most_common(200) if t not in title_set and not any(char.isdigit() for char in t) and not any(b in t for b in self.exclude_brands)]

        final_tags = []
        clusters = {'제과': ['제과', '제빵', '베이킹'], '맛': ['맛', '달달', '고소'], '영양': ['영양', '단백질'], '용도': ['자판기', '식자재']}
        used_roots = set()
        for t, c in valid_tags:
            matched = None
            for root, keywords in clusters.items():
                if any(k in t for k in keywords): matched = root; break
            if matched and matched not in used_roots: final_tags.append((t, c)); used_roots.add(matched)
        for t, c in valid_tags:
            if len(final_tags) >= 10: break
            if any(t == ex[0] for ex in final_tags): continue
            if not any(t in ex[0] or ex[0] in t for ex in final_tags): final_tags.append((t, c))
        
        return conv_keys, add_keys, readable_auto, spec_counts, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

# UI 헬퍼 함수
def calculate_bytes(text):
    return len(text.encode('euc-kr', errors='replace'))

# 3. 사이드바 및 UI
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 전략 키워드 설정")
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
    conv, add, auto, specs, tags = manager.run_analysis(conversion_input, add_input, total_kw_count)

    st.success("✨ 최적화 분석이 완료되었습니다!")

    # 섹션 1: 전략적 상품명 조합
    st.header("🏷️ 1. 전략적 상품명 조합")
    
    full_title = " ".join(conv + add + [p[0] for p in auto])
    title_len = len(full_title)
    total_kw_sum = len(conv) + len(add) + len(auto)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("✅ 완성된 상품명")
        st.code(full_title, language=None)
        
        # 가독성 요약 지표
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        
        # 총 키워드 수 표시
        m1.metric("총 키워드 수", f"{total_kw_sum}개", help="구매전환 + 추가 + 자동 키워드의 합계")
        
        # 글자 수 상태 표시 (50자 기준)
        status_color = "normal" if title_len <= 50 else "inverse"
        status_text = "🟢 정상" if title_len <= 50 else "🔴 초과 (SEO 주의)"
        m2.metric("총 글자 수", f"{title_len}자 / 50자", delta=status_text, delta_color=status_color)
        
        # 바이트 수 표시
        m3.metric("총 바이트(Byte)", f"{calculate_bytes(full_title)}B", help="네이버 쇼핑 공식 제한은 보통 100바이트 내외입니다.")

        # 세부 구성 표기
        st.markdown(f"""
        > **세부 구성:** 구매전환({len(conv)}) + 추가({len(add)}) + 자동추천({len(auto)})
        """)

    with col2:
        st.subheader("📈 자동 키워드 빈도")
        auto_df = pd.DataFrame(auto, columns=['단어', '빈도(회)'])
        auto_df.index += 1
        st.table(auto_df)

    st.markdown("---")

    # 섹션 2: 속성
    st.header("⚙️ 2. 필터 노출용 속성값")
    col3, col4 = st.columns([2, 1])
    with col3:
        for s, _ in specs: st.button(s, key=f"btn_{s}", use_container_width=True)
    with col4:
        st.table(pd.DataFrame(specs, columns=['속성값', '빈도']).set_index(pd.Index(range(1, len(specs)+1))))

    st.markdown("---")

    # 섹션 3: 태그
    st.header("🔍 3. 확장 검색 태그")
    col5, col6 = st.columns([2, 1])
    with col5:
        st.warning(", ".join([f"#{t[0]}" for t in tags]))
        st.info("**확장성:** 상품명과 겹치지 않는 서로 다른 카테고리의 유입 경로를 확보했습니다.")
    with col6:
        tag_df = pd.DataFrame(tags, columns=['태그명', '사용 빈도수'])
        tag_df.index += 1
        st.table(tag_df)

else:
    st.info("왼쪽 사이드바에서 파일을 업로드하고 설정을 확인해주세요.")
