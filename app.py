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
        # NLU 분리 기준 핵심 단어 (확장성 체크를 위해 '추억', '간식' 등 추가)
        self.sub_splits = sorted(['자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', '업소용', '대용량', '멸균', '파우치', '추억', '간식', '재료'], key=len, reverse=True)

    def split_base_terms(self, text):
        """NLU 규칙에 따라 복합 명사를 자동으로 분리하는 엔진"""
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        raw_words = text.split()
        
        terms = []
        pattern = f"({'|'.join(self.sub_splits)})"
        
        for word in raw_words:
            if word in self.exclude_brands or any(char.isdigit() for char in word):
                continue
            parts = re.split(pattern, word)
            for p in parts:
                p = p.strip()
                if not p or p in self.exclude_brands: continue
                if len(p) > 1 or p in self.sub_splits:
                    terms.append(p)
        return terms

    def reorder_for_readability(self, word_count_pairs):
        identity, form, usage, desc = ['전지', '분유', '우유', '탈지'], ['분말', '가루', '스틱', '액상'], ['자판기', '업소용', '대용량', '식자재'], ['진한', '고소한', '맛있는', '추억']
        def get_priority(pair):
            word = pair[0]
            if any(core in word for core in identity): return 1
            if any(core in word for core in form): return 2
            if any(core in word for core in usage): return 3
            if any(core in word for core in desc): return 4
            return 5
        return sorted(word_count_pairs, key=lambda x: get_priority(x))

    def run_analysis(self, conversion_input, add_input, total_target_count):
        # 1. 고정 키워드 (NLU 분리 적용)
        conv_keys = self.split_base_terms(conversion_input)
        add_keys = self.split_base_terms(add_input)
        fixed_keywords = conv_keys + add_keys
        
        # 2. 상품명 자동 추출 키워드
        name_terms = []
        for name in self.df['상품명']:
            name_terms.extend(self.split_base_terms(name))
        
        name_freq = Counter(name_terms).most_common(50)
        auto_candidates = [w for w, c in name_freq if w not in fixed_keywords]
        
        remain_count = max(0, total_target_count - len(fixed_keywords))
        selected_auto = auto_candidates[:remain_count]
        readable_auto_pairs = self.reorder_for_readability([(w, Counter(name_terms)[w]) for w in selected_auto])
        
        # 3. 속성(스펙) 분석 (로직 및 출력 유지)
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)
        # 속성에서 사용된 개별 키워드 추출
        spec_keywords = set()
        for s, _ in spec_counts:
            spec_keywords.update(self.split_base_terms(s))

        # 4. 상품명에 사용된 전체 키워드 집합
        title_keywords = set(fixed_keywords + [p[0] for p in readable_auto_pairs])

        # 5. 확장 검색 태그 분석 (확장성 극대화 업그레이드)
        tag_raw_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                tag_raw_list.extend([t.strip() for t in str(tags).split(',') if t.strip()])
        
        tag_freq = Counter(tag_raw_list).most_common(300)
        
        final_tags = []
        # 이미 선점된 태그의 '의미적 조각'들 (중복 차단용)
        master_keyword_pool = title_keywords.union(spec_keywords)

        for t_raw, c in tag_freq:
            if len(final_tags) >= 10: break
            
            # 태그를 NLU 단위로 분해
            t_subterms = self.split_base_terms(t_raw)
            if not t_subterms:
                if len(t_raw) > 1: t_subterms = [t_raw]
                else: continue
            
            # [지능형 중복 검사]
            is_redundant = False
            
            # (1) 기존 키워드 풀(상품명/속성/기선택 태그)과 조각 단어가 겹치는지 체크
            for sub in t_subterms:
                if sub in master_keyword_pool:
                    is_redundant = True; break
            
            # (2) 문자열 포함 관계 체크 (예: #제과제빵 vs #제과제빵재료)
            if not is_redundant:
                for existing_t, _ in final_tags:
                    if t_raw in existing_t or existing_t in t_raw:
                        is_redundant = True; break

            # (3) 숫자 포함 제외
            if any(char.isdigit() for char in t_raw): is_redundant = True

            if not is_redundant:
                final_tags.append((t_raw, c))
                # 뽑힌 태그의 모든 조각 단어를 풀에 추가하여 이후 유사 단어 차단
                for sub in t_subterms: master_keyword_pool.add(sub)

        return fixed_keywords, readable_auto_pairs, spec_counts, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

def calculate_seo_metrics(text):
    char_count = len(text)
    try: byte_count = len(text.encode('euc-kr'))
    except: byte_count = len(text.encode('utf-8'))
    return char_count, byte_count

# 3. GUI 구성 (레이아웃 변동 없음)
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 전략 설정")
conversion_input = st.sidebar.text_input("구매전환 키워드", placeholder="예: 맛있는자판기우유")
add_input = st.sidebar.text_input("추가할 키워드", placeholder="예: 무료배송당일발송")
total_kw_count = st.sidebar.number_input("상품명 목표 키워드 수", min_value=5, max_value=25, value=11)

if uploaded_file:
    try: df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df, [])
    fixed, auto, specs, tags = manager.run_analysis(conversion_input, add_input, total_kw_count)

    st.success("✨ NLU 기반 정밀 분석이 완료되었습니다!")

    # 섹션 1: 상품명 (변동 없음)
    st.header("🏷️ 1. 전략적 상품명 조합")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("✅ 완성된 상품명")
        full_title = " ".join(fixed + [p[0] for p in auto])
        st.code(full_title, language=None)
        c_len, b_len = calculate_seo_metrics(full_title)
        st.markdown(f"{'🟢 정상' if c_len <= 50 else '🔴 주의'}: {c_len}자 / {b_len} Byte / {len(fixed)+len(auto)}개 키워드")

    with col2:
        st.subheader("📊 자동 추천 키워드")
        st.table(pd.DataFrame(auto, columns=['단어', '빈도']).assign(No=range(1, len(auto)+1)).set_index('No'))

    st.markdown("---")

    # 섹션 2: 속성 (로직 및 출력 유지)
    st.header("⚙️ 2. 필터 노출용 속성값")
    col3, col4 = st.columns([2, 1])
    with col3:
        for s, _ in specs: st.button(s, key=f"attr_{s}", use_container_width=True)
    with col4:
        st.table(pd.DataFrame(specs, columns=['속성값', '빈도']).set_index(pd.Index(range(1, len(specs)+1))))

    st.markdown("---")

    # 섹션 3: 태그 (업그레이드된 로직 적용)
    st.header("🔍 3. 확장 검색 태그 (조합 효율 극대화)")
    col5, col6 = st.columns([2, 1])
    with col5:
        st.subheader("✅ 최적화 태그 10선")
        tag_display = ", ".join([f"#{t[0]}" for t in tags])
        st.success(tag_display)
        st.caption("※ 태그를 NLU 단위로 분해하고 문자열 포함 관계를 분석하여 유입 경로가 겹치지 않는 최적의 조합을 선별했습니다.")
    with col6:
        st.subheader("📊 태그 사용 빈도수")
        tag_df = pd.DataFrame(tags, columns=['태그명', '사용 빈도수'])
        tag_df.index += 1
        st.table(tag_df)
else:
    st.info("파일을 업로드해주세요.")
