import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from io import StringIO

st.set_page_config(page_title="성적 시각화 도구", layout="wide")

st.title("🎓 성적 시각화 앱")
st.write("CSV 파일을 업로드하면 히스토그램, 막대그래프, 산점도, 상자그림을 인터랙티브하게 그릴 수 있습니다.")

def make_sample_csv():
    # 간단한 예시 CSV 생성
    rows = []
    np.random.seed(1)
    for i in range(100):
        rows.append({
            "학생": f"학생{i+1}",
            "반": np.random.choice(["A","B","C"]),
            "수학": int(np.clip(np.random.normal(70, 15), 0, 100)),
            "영어": int(np.clip(np.random.normal(65, 12), 0, 100)),
            "과학": int(np.clip(np.random.normal(75, 10), 0, 100)),
        })
    df = pd.DataFrame(rows)
    # 와이드 포맷(학생 × 과목)을 롱포맷으로 변환하지 않고 그대로 제공
    return df

st.sidebar.header("데이터 입력")
upload = st.sidebar.file_uploader("CSV 파일 업로드", type=["csv"]) 
if st.sidebar.button("샘플 CSV 생성/로드"):
    sample_df = make_sample_csv()
    csv_buf = sample_df.to_csv(index=False)
    st.sidebar.download_button("샘플 CSV 다운로드", csv_buf, file_name="sample_grades.csv")

# 데이터 로드
df = None
if upload is not None:
    try:
        df = pd.read_csv(upload)
    except Exception as e:
        st.sidebar.error(f"CSV 로드 오류: {e}")

if df is None:
    st.info("CSV 파일을 업로드하면 시작됩니다. 샘플 파일을 원하면 사이드바에서 생성 후 다운로드 하세요.")
    st.stop()

# 사용자 편의를 위한 칼럼 타입 분류
df.columns = [c.strip() for c in df.columns]
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
all_cols = df.columns.tolist()
categorical_cols = [c for c in all_cols if c not in numeric_cols]

st.header("데이터 미리보기")
st.dataframe(df.head(200))

st.sidebar.header("그래프 선택")
show_hist = st.sidebar.checkbox("히스토그램", value=True)
show_bar = st.sidebar.checkbox("막대그래프", value=True)
show_scatter = st.sidebar.checkbox("산점도", value=True)
show_box = st.sidebar.checkbox("상자그림", value=True)

st.markdown("---")

def draw_histogram(df):
    with st.expander("히스토그램 설정 / 그리기"):
        if not numeric_cols:
            st.warning("수치형 컬럼이 없습니다.")
            return
        col = st.selectbox("히스토그램 변수 (수치형)", numeric_cols)
        bins = st.slider("빈 개수 (maxbins)", 5, 100, 30)
        log_scale = st.checkbox("로그 스케일", value=False)
        chart = alt.Chart(df).mark_bar().encode(
            alt.X(f"{col}:Q", bin=alt.Bin(maxbins=bins), title=col),
            y='count()',
            tooltip=[alt.Tooltip(f"{col}:Q", title=col)]
        )
        if log_scale:
            chart = chart.encode(y=alt.Y('count()', scale=alt.Scale(type='log')))
        st.altair_chart(chart, use_container_width=True)

def draw_bar(df):
    with st.expander("막대그래프 설정 / 그리기"):
        if not categorical_cols and not numeric_cols:
            st.warning("사용 가능한 컬럼이 없습니다.")
            return
        x_col = st.selectbox("X (범주형 권장)", categorical_cols + numeric_cols, index=0)
        y_col = st.selectbox("Y (집계할 수치형) - 선택 안 하면 빈도수", [None] + numeric_cols)
        agg = st.selectbox("집계 함수", ['mean', 'sum', 'count'])
        if y_col is None and agg != 'count':
            st.info("Y를 선택하지 않으면 'count'로만 집계됩니다.")
        if agg == 'count' or y_col is None:
            agg_df = df.groupby(x_col).size().reset_index(name='count')
            chart = alt.Chart(agg_df).mark_bar().encode(x=f"{x_col}:N", y='count:Q', tooltip=[x_col, 'count'])
        else:
            if agg == 'mean':
                agg_df = df.groupby(x_col)[y_col].mean().reset_index()
            else:
                agg_df = df.groupby(x_col)[y_col].sum().reset_index()
            chart = alt.Chart(agg_df).mark_bar().encode(x=f"{x_col}:N", y=f"{y_col}:Q", tooltip=[x_col, alt.Tooltip(f"{y_col}:Q", format='.2f')])
        st.altair_chart(chart, use_container_width=True)

def draw_scatter(df):
    with st.expander("산점도 설정 / 그리기"):
        if len(numeric_cols) < 2:
            st.warning("산점도에는 최소 2개의 수치형 컬럼이 필요합니다.")
            return
        x = st.selectbox("X (수치형)", numeric_cols, index=0)
        y = st.selectbox("Y (수치형)", [c for c in numeric_cols if c != x], index=0)
        color = st.selectbox("색상 (범주형 선택)", [None] + categorical_cols)
        size = st.selectbox("점 크기 (수치형 선택)", [None] + numeric_cols)
        chart = alt.Chart(df).mark_circle(opacity=0.7).encode(
            x=alt.X(f"{x}:Q", title=x),
            y=alt.Y(f"{y}:Q", title=y),
            tooltip=[x, y]
        )
        if color is not None:
            chart = chart.encode(color=f"{color}:N")
        if size is not None:
            chart = chart.encode(size=f"{size}:Q")
        st.altair_chart(chart.interactive(), use_container_width=True)

def draw_box(df):
    with st.expander("상자그림 설정 / 그리기"):
        if not numeric_cols:
            st.warning("수치형 컬럼이 없습니다.")
            return
        y = st.selectbox("Y (수치형)", numeric_cols, index=0)
        x = st.selectbox("X (범주형, 선택사항)", [None] + categorical_cols)
        if x is None:
            chart = alt.Chart(df).mark_boxplot().encode(y=f"{y}:Q")
        else:
            chart = alt.Chart(df).mark_boxplot().encode(x=f"{x}:N", y=f"{y}:Q", color=f"{x}:N")
        st.altair_chart(chart, use_container_width=True)

# 각 차트 렌더링
if show_hist:
    draw_histogram(df)
if show_bar:
    draw_bar(df)
if show_scatter:
    draw_scatter(df)
if show_box:
    draw_box(df)

# 정렬된 데이터 테이블 및 다운로드 제공
st.markdown("---")
st.subheader("데이터 테이블")
st.dataframe(df)
st.download_button("전체 데이터 다운로드 (CSV)", df.to_csv(index=False), file_name="uploaded_data.csv", mime='text/csv')

st.info("각 그래프 제목을 클릭(확장)하면 데이터에 맞춰 변수를 선택할 수 있습니다.")
