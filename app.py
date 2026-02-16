if uploaded_file:
    # 1. 파일 읽기 시도
    try:
        # 첫 번째 시도: cp949 (보통 엑셀에서 저장한 CSV)
        df = pd.read_csv(uploaded_file, encoding='cp949')
    except Exception:
        # ★ 중요: 첫 번째 시도에서 에러가 나면 파일 포인터가 끝으로 이동합니다.
        # 다시 읽기 위해 포인터를 맨 앞으로 되돌립니다.
        uploaded_file.seek(0)
        
        try:
            # 두 번째 시도: utf-8-sig (한글 포함된 일반적인 CSV)
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        except Exception as e:
            # 두 번 다 실패할 경우 에러 메시지 출력
            st.error(f"파일을 읽는 중 에러가 발생했습니다: {e}")
            df = None

    if df is not None:
        if df.empty:
            st.warning("업로드한 파일에 데이터가 없습니다.")
        else:
            manager = SEOManager(df)
            names, specs, tags = manager.run_analysis()
            
            # (이후 출력 로직은 동일...)
            st.success("✅ 분석이 완료되었습니다!")
            # ... 생략 ...
