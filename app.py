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
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        pattern = f"({'|'.join(self.sub_splits)})"
        raw_parts = re.split(pattern, text)
        terms = []
        for part in raw_parts:
            p = part.strip()
            if not p or p in self.exclude_brands or any(c.isdigit() for c in p): continue
            if len(p) > 1 or p in self.sub_splits: terms.append(p)
        return terms

    def process_naver_stats(self, stats_file):
        """스마트스토어 통계 엑셀에서 실제 구매 키워드 추출"""
        try:
            # 네이버 통계 파일은 보통 cp949 인코딩입니다.
            sdf = pd.read_csv(stats_file, encoding='cp949')
        except:
            stats_file.seek(0)
            sdf = pd.read_csv(stats_file, encoding='utf-8-sig')
        
        # '검색키워드' 열과 '결제수' 혹은 '결제금액' 기준 정렬 (이미지 기반 컬럼명 추정)
        target_col = '검색키워드'
        if target_col in sdf.columns:
            # 결제수가 높은 순서대로 유효 키워드 추출
            valid_stats = sdf[sdf[target_col] != '-'].copy()
            return valid_stats[target_col].unique().tolist()[:20]
        return []

    def run_analysis(self, selected_keywords, manual_input, add_input, total_target_count):
        conv_keys = list(selected_keywords) + self.split_base_terms(manual_input)
        add_keys = self.split_base_terms(add_input)
        fixed_keywords = conv_keys + add_keys
        
        name_terms = []
        for name in self.df['상품명']: name_terms.extend(self.split_base_terms(name))
        name_freq = Counter(name_terms).most_common(100)
        
        auto_candidates = [w for w, c in name_freq if w not in fixed_keywords]
        remain_count = max(0, total_target_count - len(fixed_keywords))
        selected_auto = auto_candidates[:remain_count]
        readable_auto_pairs = self.reorder_for_readability([(w, Counter(name_terms)[w]) for w in selected_auto])
        
        # 2. 속성(기존 유지)
        spec_list = []
        for spec in self.df['스펙'].dropna():
            parts = [p.strip() for p in str(spec).split('|')]
            spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)
        spec_keywords = set([s[0] for s in spec_counts])

        # 3. 태그(기존 유지 - 확장성 극대화)
        tag_raw_list = []
        for tags in self.df['검색인식태그'].dropna():
            tag_raw_list.extend([t.strip() for t in str(tags).split(',') if t.strip()])
        tag_freq = Counter(tag_raw_list).most_common(300)
        
        title_keywords = set(fixed_keywords + [p[0] for p in readable_auto_pairs])
        final_tags, selected_subterms = [], set()
        master_pool = title_keywords.union(spec_keywords)

        for t_raw, c in tag_freq:
            if len(final_tags) >= 10: break
            if any(brand in t_raw for brand in self.exclude_brands): continue
            t_subterms = self.split_base_terms(t_raw)
            if not t_subterms: continue
            
            is_redundant = False
            for sub in t_subterms:
                if sub in master_pool or sub in selected_subterms:
                    is_redundant = True; break
            
            if not is_redundant:
                for ex_t, _ in final_tags:
                    if t_raw in ex_t or ex_t in t_raw:
                        is_redundant = True; break

            if not is_redundant:
                final_tags.append((t_raw, c))
                for sub in t_subterms: selected_subterms.add(sub)

        return fixed_keywords, readable_auto_pairs, spec_counts, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

    def reorder_for_readability(self, pairs):
        identity, form, usage = ['전지', '분유', '우유'], ['가루', '분말'], ['자판기', '업소용']
        def get_priority(pair):
            w = pair[0]
            if any(c in w for c in identity): return 1
            if any(c in w for c in form): return 2
            if any(c in w for c in usage): return 3
            return 4
        return sorted(pairs, key=lambda x: get_priority(x))

def calculate_seo_metrics(text):
    c_len = len(text)
    try: b_len = len(text.encode('euc-kr'))
    except: b_len = len(text.encode('utf-8'))
    return c_len, b_len

# 3. GUI 구성
st.sidebar.header("📁 Step 1. 데이터 업로드")
main_file = st.sidebar.file_uploader("1️⃣ 분석용 상품 데이터 (CSV)", type=["csv"])
stats_file = st.sidebar.file_uploader("2️⃣ [선택] 네이버 결제 통계 (CSV)", type=["csv"], help="스마트스토어센터 > 판매분석 > 상품/검색채널에서 다운로드한 파일")

if main_file:
    try: df = pd.read_csv(main_file, encoding='cp949')
    except: df = pd.read_csv(main_file, encoding='utf-8-sig')

    manager = SEOManager(df, [])
    
    # 통계 파일이 있으면 구매 키워드 자동 추출
    stats_keywords = []
    if stats_file:
        stats_keywords = manager.process_naver_stats(stats_file)
        if stats_keywords:
            st.sidebar.success(f"✔️ 결제 키워드 {len(stats_keywords)}개 로드 완료!")

    st.sidebar.header("🎯 Step 2. 키워드 선택")
    # 통계 키워드와 일반 상위 키워드를 통합하여 픽커 구성
    all_picks = stats_keywords + [k for k in [p[0] for p in Counter(df['상품명'].apply(manager.split_base_terms).sum()).most_common(30)] if k not in stats_keywords]
    
    selected_pick = st.sidebar.multiselect("결제/인기 키워드 픽커", options=all_picks, default=stats_keywords[:5] if stats_keywords else [])
    manual_in = st.sidebar.text_input("직접 입력", placeholder="예: 맛있는자판기우유")
    add_in = st.sidebar.text_input("추가 배치 키워드")
    total_kw = st.sidebar.number_input("상품명 목표 키워드 수", value=11)

    fixed, auto, specs, tags = manager.run_analysis(selected_pick, manual_in, add_in, total_kw)

    # 출력 섹션 (매니저님 요청대로 유지)
    st.header("🏷️ 1. 전략적 상품명 조합")
    full_title = " ".join(fixed + [p[0] for p in auto])
    st.code(full_title, language=None)
    c_l, b_l = calculate_seo_metrics(full_title)
    st.markdown(f"{'🟢 정상' if c_l <= 50 else '🔴 주의'}: **{c_l}자 / {b_l} Byte / {len(fixed)+len(auto)}개 키워드**")
    
    st.markdown("---")
    st.header("⚙️ 2. 필터 속성 & 🔍 3. 확장 태그")
    l_col, r_col = st.columns(2)
    with l_col:
        for s_name, _ in specs: st.button(s_name, use_container_width=True, key=f"btn_{s_name}")
    with r_col:
        st.success(", ".join([f"#{t[0]}" for t in tags]))
else:
    st.info("사이드바에서 파일을 업로드해주세요.")
