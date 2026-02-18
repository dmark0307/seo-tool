import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정 및 디자인
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
        self.sub_splits = sorted(['자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', '업소용', '대용량', '멸균', '파우치', '추억', '간식', '재료'], key=len, reverse=True)

    def split_base_terms(self, text):
        """NLU 규칙에 따라 복합 명사를 자동으로 분리하는 엔진"""
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        raw_words = text.split()
        terms = []
        pattern = f"({'|'.join(self.sub_splits)})"
        for word in raw_words:
            if word in self.exclude_brands or any(char.isdigit() for char in word): continue
            parts = re.split(pattern, word)
            for p in parts:
                p = p.strip()
                if not p or p in self.exclude_brands: continue
                if len(p) > 1 or p in self.sub_splits: terms.append(p)
        return terms

    def extract_stats_keywords(self, stats_df, target_product_code):
        """네이버 판매분석 통계 데이터에서 특정 상품코드의 결제 키워드 추출"""
        try:
            # 보통 네이버 통계 시트의 상품번호 컬럼명은 '상품번호' 또는 '상품ID'입니다.
            # 데이터에서 해당 상품코드와 매칭되는 행만 필터링합니다.
            code_col = [c for c in stats_df.columns if '번호' in c or 'ID' in c or '코드' in c][0]
            kw_col = [c for c in stats_df.columns if '키워드' in c][0]
            
            # 상품코드 매칭 (문자열 변환 후 비교)
            filtered_df = stats_df[stats_df[code_col].astype(str) == str(target_product_code)]
            
            # 검색키워드 추출 및 정제
            raw_keywords = filtered_df[kw_col].dropna().unique().tolist()
            extracted = []
            for rk in raw_keywords:
                if rk != '-': extracted.extend(self.split_base_terms(rk))
            return list(dict.fromkeys(extracted))[:5] # 상위 5개 추출
        except Exception as e:
            return []

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

    def run_analysis(self, stats_keywords, conversion_input, add_input, total_target_count):
        # 통계에서 추출한 키워드 + 직접 입력한 키워드 통합
        conv_keys = stats_keywords + self.split_base_terms(conversion_input)
        add_keys = self.split_base_terms(add_input)
        fixed_keywords = []
        for k in (conv_keys + add_keys):
            if k not in fixed_keywords: fixed_keywords.append(k)
        
        name_terms = []
        for name in self.df['상품명']: name_terms.extend(self.split_base_terms(name))
        name_freq = Counter(name_terms).most_common(50)
        auto_candidates = [w for w, c in name_freq if w not in fixed_keywords]
        
        remain_count = max(0, total_target_count - len(fixed_keywords))
        selected_auto = auto_candidates[:remain_count]
        readable_auto_pairs = self.reorder_for_readability([(w, Counter(name_terms)[w]) for w in selected_auto])
        
        # 2. 필터 노출용 속성값 분석 (로직 유지)
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)
        spec_keywords = set()
        for s, _ in spec_counts: spec_keywords.update(self.split_base_terms(s))

        title_keywords = set(fixed_keywords + [p[0] for p in readable_auto_pairs])

        # 3. 확장 검색 태그 분석 (로직 유지)
        tag_raw_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                tag_raw_list.extend([t.strip() for t in str(tags).split(',') if t.strip()])
        tag_freq = Counter(tag_raw_list).most_common(300)
        candidates = []
        for t_raw, c in tag_freq:
            if any(brand in t_raw for brand in self.exclude_brands): continue
            if any(char.isdigit() for char in t_raw): continue
            t_subterms = self.split_base_terms(t_raw)
            if not t_subterms or any(sub in title_keywords or sub in spec_keywords for sub in t_subterms): continue
            candidates.append((t_raw, c))

        final_tags, selected_subterms = [], set()
        for i, (t_raw, c) in enumerate(candidates):
            if len(final_tags) >= 10: break
            is_shorter_redundant = False
            for j, (other_t, other_c) in enumerate(candidates):
                if i != j and t_raw in other_t and len(t_raw) < len(other_t):
                    is_shorter_redundant = True; break
            if is_shorter_redundant: continue
            prefix = t_raw[:3] if len(t_raw) > 3 else t_raw[:2]
            if any(prefix in ex_t or ex_t[:3] in t_raw for ex_t, _ in final_tags): continue
            t_subterms = self.split_base_terms(t_raw)
            if any(sub in selected_subterms for sub in t_subterms): continue
            final_tags.append((t_raw, c)); selected_subterms.update(t_subterms)

        return fixed_keywords, readable_auto_pairs, spec_counts, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

def calculate_seo_metrics(text):
    c_len = len(text)
    try: b_len = len(text.encode('euc-kr'))
    except: b_len = len(text.encode('utf-8'))
    return c_len, b_len

# 3. GUI 구성
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("1️⃣ 분석용 상품 데이터 (CSV)", type=["csv"])
stats_file = st.sidebar.file_uploader("2️⃣ 판매분석 통계 데이터 (CSV/Excel)", type=["csv", "xlsx"])
target_code = st.sidebar.text_input("🎯 최적화할 상품코드 입력", placeholder="예: 123456789")

st.sidebar.header("🎯 Step 2. 전략 설정")
conversion_input = st.sidebar.text_input("구매전환 키워드 (추가)", placeholder="통계 외 추가할 키워드")
add_input = st.sidebar.text_input("추가할 키워드")
total_kw_count = st.sidebar.number_input("상품명 목표 키워드 수", min_value=5, max_value=25, value=11)

if uploaded_file:
    try:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')

    manager = SEOManager(df, [])
    
    # 통계 기반 구매전환 키워드 추출 로직
    stats_kws = []
    if stats_file and target_code:
        try:
            if stats_file.name.endswith('.csv'):
                try: stats_df = pd.read_csv(stats_file, encoding='cp949')
                except: stats_df = pd.read_csv(stats_file, encoding='utf-8-sig')
            else:
                stats_df = pd.read_excel(stats_file)
            stats_kws = manager.extract_stats_keywords(stats_df, target_code)
            if stats_kws: st.sidebar.success(f"✔️ 상품코드 {target_code}의 결제 키워드 추출 완료!")
            else: st.sidebar.warning("매칭되는 상품코드나 키워드가 없습니다.")
        except Exception as e:
            st.sidebar.error(f"통계 파일 분석 오류: {e}")

    fixed, auto, specs, tags = manager.run_analysis(stats_kws, conversion_input, add_input, total_kw_count)

    st.success("✨ 판매 통계 매칭 분석이 완료되었습니다!")

    # 1. 전략적 상품명 조합
    st.header("🏷️ 1. 전략적 상품명 조합")
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("✅ 완성된 상품명")
        full_title = " ".join(fixed + [p[0] for p in auto])
        st.code(full_title, language=None)
        c_len, b_len = calculate_seo_metrics(full_title)
        st.markdown(f"{'🟢 정상' if c_len <= 50 else '🔴 주의'}: {c_len}자 / {b_len} Byte / {len(fixed)+len(auto)}개 키워드")
        if stats_kws: st.info(f"📊 **통계 반영 키워드:** {', '.join(stats_kws)}")

    with col2:
        st.subheader("📊 자동 추천 빈도")
        st.table(pd.DataFrame(auto, columns=['단어', '빈도']).assign(No=range(1, len(auto)+1)).set_index('No'))

    st.markdown("---")
    # 2. 필터 노출용 속성값 (변동 없음)
    st.header("⚙️ 2. 필터 노출용 속성값")
    col3, col4 = st.columns([2, 1])
    with col3:
        for s, _ in specs: st.button(s, key=f"attr_{s}", use_container_width=True)
    with col4:
        st.table(pd.DataFrame(specs, columns=['속성값', '빈도']).set_index(pd.Index(range(1, len(specs)+1))))

    st.markdown("---")
    # 3. 확장 검색 태그 (변동 없음)
    st.header("🔍 3. 확장 검색 태그 (조합 효율 극대화)")
    col5, col6 = st.columns([2, 1])
    with col5:
        st.subheader("✅ 최적화 태그 10선")
        st.success(", ".join([f"#{t[0]}" for t in tags]))
        st.caption("※ 짧은 단어보다 정보량이 풍부한 조합 키워드를 우선 선택하여 검색 노출을 확장했습니다.")
    with col6:
        st.subheader("📊 태그 사용 빈도수")
        st.table(pd.DataFrame(tags, columns=['태그명', '사용 빈도수']).assign(No=range(1, len(tags)+1)).set_index('No'))
else:
    st.info("사이드바에서 상품 데이터와 통계 파일을 업로드해주세요.")
