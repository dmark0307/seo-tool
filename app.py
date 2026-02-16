import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정
st.set_page_config(page_title="네이버 SEO 통합 분석 도구", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 매니저")
st.markdown("---")

# 2. 전문 SEO 분석 로직 클래스
class SEOManager:
    def __init__(self, df):
        self.df = df
        self.exclude_brands = [
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ]

    def split_base_terms(self, text):
        """복합 명사를 분리하여 기초 단어(Base Term) 추출 및 수치값/브랜드 제거"""
        if pd.isna(text) or text == '-': return []
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', str(text))
        raw_words = text.split()
        
        terms = []
        sub_splits = ['자판기', '우유', '분유', '가루', '분말', '전지', '탈지', '스틱', '업소용', '대용량']
        
        for word in raw_words:
            # 브랜드명 제외 + 숫자가 포함된 단어(1kg 등) 전체 제외
            if word in self.exclude_brands or any(char.isdigit() for char in word):
                continue
            
            found_sub = False
            for sub in sub_splits:
                if sub in word and word != sub:
                    terms.append(sub)
                    rem = word.replace(sub, '').strip()
                    if len(rem) > 1 and not any(char.isdigit() for char in rem):
                        terms.append(rem)
                    found_sub = True
                    break
            if not found_sub and len(word) > 1:
                terms.append(word)
        return terms

    def run_analysis(self, manual_input):
        # [0] 수동 입력 키워드 정리 (공백 기준 분리)
        manual_keywords = [w.strip() for w in manual_input.split() if len(w.strip()) > 0]
        
        # [1] 상품명 분석
        name_terms = []
        for name in self.df['상품명']:
            name_terms.extend(self.split_base_terms(name))
        
        name_freq = Counter(name_terms).most_common(50)
        
        # 수동 입력 키워드와 중복되지 않는 자동 키워드 선별
        auto_names_with_count = []
        for w, c in name_freq:
            # 수동 키워드에 포함된 단어는 제외
            if not any(manual_w in w or w in manual_w for manual_w in manual_keywords):
                auto_names_with_count.append((w, c))
        
        # 최종 상품명 조합 (수동 + 자동 합쳐서 12단어 내외)
        remain_count = max(0, 12 - len(manual_keywords))
        top_auto_names = auto_names_with_count[:remain_count]
        
        # [2] 속성 분석
        spec_list = []
        for spec in self.df['스펙'].dropna():
            if spec != '-':
                parts = [p.strip() for p in str(spec).split('|')]
                spec_list.extend([p for p in parts if len(p) > 1 and p not in self.exclude_brands])
        spec_counts = Counter(spec_list).most_common(8)

        # [3] 태그 분석
        tag_list = []
        for tags in self.df['검색인식태그'].dropna():
            if tags != '-':
                parts = [t.strip() for t in str(tags).split(',')]
                tag_list.extend([t for t in parts if not any(b in t for b in self.exclude_brands)])
        
        tag_freq = Counter(tag_list).most_common(100)
        
        # 상품명(수동+자동) 전체와 중복되지 않는 태그 선별
        current_title_words = manual_keywords + [n[0] for n in top_auto_names]
        candidates = []
        for t, c in tag_freq:
            if not any(char.isdigit() for char in t) and not any(word in t for word in current_title_words):
                candidates.append({'tag': t, 'count': c})
        
        # 태그간 확장성/중복 로직 (A가 B에 포함되면 A 탈락)
        tags_to_skip = set()
        for i in range(len(candidates)):
            t1 = candidates[i]['tag']
            for j in range(len(candidates)):
                if i == j: continue
                t2 = candidates[j]['tag']
                if t1 in t2:
                    tags_to_skip.add(t1)
                    break
        
        final_pool = [c for c in candidates if c['tag'] not in tags_to_skip]
        final_tags = [(c['tag'], c['count']) for c in final_pool[:10]]
        
        return manual_keywords, top_auto_names, spec_counts, final_tags

# 3. 사용자 인터페이스 (GUI)
st.sidebar.header("📁 Step 1. 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("분석용 CSV 파일 업로드", type=["csv"])

st.sidebar.header("🎯 Step 2. 수동 키워드 설정")
manual_input = st.sidebar.text_input(
    "실제 구매 유입 키워드 입력", 
    placeholder="예: 맛있는 속편한 국내산",
    help="여기에 입력한 키워드는 상품명 맨 앞에 고정 배치되며, 자동 분석에서 제외됩니다."
)

if uploaded_file:
    df = None
    try:
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except:
        uploaded_file.seek(0)
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")

    if df is not None:
        manager = SEOManager(df)
        manual_keys, auto_keys, specs, tags = manager.run_analysis(manual_input)

        st.success("✨ 분석이 완료되었습니다. 수동 키워드를 우선 배치하여 최적화했습니다.")

        # --- 섹션 1: 상품명 ---
        st.header("🏷️ 1. 전략적 상품명 조합 (구매 키워드 반영)")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("✅ 완성된 상품명")
            full_title = " ".join(manual_keys + [n[0] for n in auto_keys])
            st.code(full_title, language=None)
            st.info(f"**전략:** 입력하신 유입 키워드({len(manual_keys)}개)를 전면에 배치하고, AI가 분석한 핵심 단어({len(auto_keys)}개)를 뒤에 붙여 총 {len(manual_keys)+len(auto_keys)}단어로 구성했습니다.")
        
        with col2:
            st.subheader("📊 자동 선별 키워드 빈도")
            name_df = pd.DataFrame(auto_keys, columns=['단어', '빈도'])
            st.table(name_df)

        st.markdown("---")

        # --- 섹션 2: 속성 키워드 ---
        st.header("⚙️ 2. 필터 노출용 속성값")
        col3, col4 = st.columns([2, 1])
        with col3:
            st.subheader("✅ 권장 속성 리스트")
            for s, c in specs:
                st.button(f"{s}", key=f"attr_{s}", use_container_width=True)
        with col4:
            st.subheader("📊 속성 인식 데이터")
            spec_df = pd.DataFrame(specs, columns=['속성값', '빈도'])
            st.table(spec_df)

        st.markdown("---")

        # --- 섹션 3: 확장 태그 ---
        st.header("🔍 3. 중복 제거 확장 태그")
        col5, col6 = st.columns([2, 1])
        with col5:
            st.subheader("✅ 최종 태그 10선")
            tag_display = ", ".join([f"#{t[0]}" for t in tags])
            st.warning(tag_display)
            st.info("**확장 로직:** 상품명(수동+자동)에 이미 포함된 단어는 태그에서 자동 배제되어 검색 그물망을 최대한 넓혔습니다.")
        with col6:
            st.subheader("📊 태그 인식 데이터")
            tag_df = pd.DataFrame(tags, columns=['태그명', '빈도'])
            st.table(tag_df)

        with st.expander("💡 [매니저 필독] 로직 상세 설명"):
            st.write(f"""
            1. **수동 키워드 우선순위:** 입력창에 넣은 '{manual_input}'은 검색 가중치가 가장 높은 상품명 맨 앞자리를 차지합니다.
            2. **자동 단어 중복 필터링:** AI는 수동 입력된 단어와 의미가 겹치는 단어를 후보에서 자동으로 빼서, 단어 낭비를 막습니다.
            3. **수치값/브랜드 차단:** 클레임 방지를 위해 1kg, 20kg 등 숫자 포함 단어와 경쟁사 브랜드명은 AI 분석에서 제외되었습니다.
            4. **태그 확장성:** 상품명에 이미 노출된 단어를 태그에 쓰지 않음으로써, 더 많은 잠재 고객(예: #식자재, #제과제빵재료 등)의 검색 결과에 내 상품을 노출시킵니다.
            """)
else:
    st.info("왼쪽 사이드바에서 CSV 파일을 업로드하고, 실제 유입 키워드를 입력해보세요.")
