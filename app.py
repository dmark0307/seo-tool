import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 (검색 확장성 마스터)")
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
            if word in self.exclude_brands or any(char.isdigit() for char in word): continue
            found_sub = False
            for sub in sub_splits:
                if sub in word and word != sub:
                    terms.append(sub)
                    rem = word.replace(sub, '').strip()
                    if len(rem) > 1 and not any(char.isdigit() for char in rem) and rem not in self.exclude_brands:
                        terms.append(rem)
                    found_sub = True
                    break
            if not found_sub and len(word) > 1: terms.append(word)
        return terms

    def reorder_for_readability(self, word_count_pairs):
        identity, form, usage, desc = ['전지', '분유', '우유', '탈지'], ['분말', '가루', '스틱', '액상'], ['자판기', '업소용', '대용량', '식자재', '제과', '제빵'], ['진한', '고소한', '맛있는', '추억']
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
        for name in self.df['상품명']: name_terms.extend(self.split_base_terms(name))
        name_freq = Counter(name_terms).most_common(50)
        auto_candidates = [(w, c) for w, c in name_freq if not any(fixed_w in w or w in fixed_w for fixed_w in fixed_keywords)]
        
        auto_pairs = auto_candidates[:max(0, total_target_count - len(fixed_keywords))]
        readable_auto = self.reorder_for_readability(auto_pairs)
        
        # 태그 분석 로직 - ★ 수식어 중복 배제 및 확장성 강화 ★
        tag_raw_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                tag_raw_list.extend([t.strip() for t in str(tags).split(',') if not any(b in t for b in self.exclude_brands)])
        
        tag_freq = Counter(tag_raw_list).most_common(150)
        title_words = set(fixed_keywords + [p[0] for p in readable_auto])
        
        candidates = [(t, c) for t, c in tag_freq if not any(char.isdigit() for char in t) and t not in title_words]

        final_tags = []
        used_prefixes = set() # "추억의", "맛있는" 등 앞부분 중복 체크용

        for t, c in candidates:
            if len(final_tags) >= 10: break
            
            # 수식어 추출 (앞 3글자 기준 또는 특정 패턴)
            # 예: "추억의맛" -> "추억의", "아이간식" -> "아이"
            prefix = t[:3] if len(t) > 3 else t[:2]
            
            # 이미 선점된 수식어이거나 상호 포함 관계인 경우 건너뜀 (확장성 극대화)
            is_redundant = False
            for existing_t, _ in final_tags:
                # 1. 수식어(앞부분)가 겹치는지 체크 (추억의맛 vs 추억의간식 방지)
                if prefix in existing_t or any(existing_t[:3] in t for existing_t, _ in final_tags if len(existing_t) > 2):
                    is_redundant = True
                # 2. 포함 관계 체크 (제과제빵 vs 제과제빵재료 중 긴 것 선택)
                if t in existing_t: # 더 긴 단어가 이미 있음
                    is_redundant = True
                elif existing_t in t: # 현재 단어가 더 길면 교체 로직 (이번 회차에선 생략하고 다음으로 넘김)
                    is_redundant = True
            
            if not is_redundant:
                final_tags.append((t, c))
                used_prefixes.add(prefix)

        # 10개가 안 채워졌을 경우 보충
        for t, c in candidates:
            if len(final_tags) >= 10: break
            if not any(t == ex[0] for ex in final_tags):
                final_tags.append((t, c))

        return conv_keys, add_keys, readable_auto, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

def check_seo(text):
    c_len = len(text)
    try: b_len = len(text.encode('euc-kr'))
    except: b_len = len(text.encode('utf-8'))
    return c_len, b_len

# 3. UI
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 전략 키워드 설정")
conv_in = st.sidebar.text_input("구매전환 키워드")
add_in = st.sidebar.text_input("추가할 키워드")
total_kw = st.sidebar.number_input("상품명 총 키워드 수", min_value=5, max_value=25, value=11)

if uploaded_file:
    df = pd.read_csv(uploaded_file, encoding='cp949') if 'cp949' else pd.read_csv(uploaded_file, encoding='utf-8-sig')
    manager = SEOManager(df, [])
    conv, add, auto, tags = manager.run_analysis(conv_in, add_in, total_kw)

    st.header("🏷️ 1. 전략적 상품명 조합")
    full_title = " ".join(conv + add + [p[0] for p in auto])
    c_len, b_len = check_seo(full_title)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.code(full_title, language=None)
        st.markdown(f"**상태:** {'🟢 정상' if c_len <= 50 else '🔴 초과'} | **글자수:** {c_len}자 | **바이트:** {b_len}B")
        st.metric("총 사용 키워드 수", f"{len(conv)+len(add)+len(auto)}개")
    with col2:
        st.table(pd.DataFrame(auto, columns=['단어', '빈도']).assign(No=range(1, len(auto)+1)).set_index('No'))

    st.markdown("---")
    st.header("🔍 3. 확장 검색 태그 (조합 확장성 극대화)")
    t_col1, t_col2 = st.columns([2, 1])
    with t_col1:
        st.success(", ".join([f"#{t[0]}" for t in tags]))
        st.info("💡 **확장 전략 적용:** '추억의'와 같은 중복 수식어를 배제하고, 최대한 다양한 유입 경로(맛, 용도, 타겟)를 확보했습니다.")
    with t_col2:
        st.table(pd.DataFrame(tags, columns=['태그명', '사용 빈도수']).assign(No=range(1, len(tags)+1)).set_index('No'))
