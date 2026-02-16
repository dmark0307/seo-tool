import streamlit as st
import pandas as pd
import re
from collections import Counter

# 1. 페이지 설정
st.set_page_config(page_title="네이버 SEO NLU 마스터", layout="wide")
st.title("🚀 네이버 쇼핑 SEO 통합 최적화 (정밀 카운팅 & 확장성 마스터)")
st.markdown("---")

class SEOManager:
    def __init__(self, df, user_exclude_list):
        self.df = df
        self.exclude_brands = [
            '매일', '서울우유', '서울', '연세', '남양', '건국', '파스퇴르', '일동', '후디스', 
            '소와나무', '빙그레', '셀로몬', '빅원더', '미광스토어', '데어리마켓', '도남상회', 
            '희창유업', '담터', '연세유업', '매일유업'
        ] + user_exclude_list

    def clean_term(self, text):
        """보이지 않는 문자 및 공백을 완벽히 제거하여 데이터 정규화"""
        if pd.isna(text): return ""
        # 제어 문자 및 불필요한 공백 제거
        text = re.sub(r'[\x00-\x1F\x7F]', '', str(text))
        return text.strip()

    def run_analysis(self, conversion_input, add_input, total_target_count):
        # [1] 고정 키워드 설정
        conv_keys = [self.clean_term(w) for w in conversion_input.split() if w.strip()]
        add_keys = [self.clean_term(w) for w in add_input.split() if w.strip()]
        fixed_keywords = conv_keys + add_keys
        
        # [2] 태그 분석 - ★ 오차 없는 정밀 카운팅 로직 ★
        tag_raw_list = []
        for row in self.df['검색인식태그'].dropna():
            if row != '-':
                # 쉼표로 분리 후 각 태그를 극한으로 정제(Clean)
                parts = [self.clean_term(t) for t in str(row).split(',') if self.clean_term(t)]
                tag_raw_list.extend(parts)
        
        # 필터링 전 원본 전체 빈도수 계산 (엑셀 숫자와 일치시키는 핵심)
        tag_freq_map = Counter(tag_raw_list)
        
        # [3] 상품명 분석 (태그 제외용)
        # (기존 상품명 분석 로직은 유지하되 태그 빈도수에 영향을 주지 않도록 분리)
        
        # [4] 확장성 기반 태그 선별
        current_title_set = set(fixed_keywords) # 상품명 확정 전이므로 우선 고정 키워드 기준
        
        valid_candidates = []
        for tag, count in tag_freq_map.most_common(500):
            if any(b in tag for b in self.exclude_brands) or any(c.isdigit() for c in tag): continue
            if tag in current_title_set: continue
            valid_candidates.append((tag, count))

        # 조합 확장성 극대화 (유사 의미 분산 배치)
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
            if any(t == ex[0] for ex in final_tags): continue
            is_redundant = False
            for ex_t, _ in final_tags:
                if t == ex_t: is_redundant = True; break
            if not is_redundant: final_tags.append((t, c))
        
        return fixed_keywords, sorted(final_tags, key=lambda x: x[1], reverse=True)[:10]

# --- UI 레이아웃 생략 (기존과 동일) ---
# (위 SEOManager 클래스의 정교해진 clean_term과 tag 분석 로직을 적용하시면 됩니다.)
