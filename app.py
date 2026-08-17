import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import requests
import urllib.parse
import re


# =========================================================
# 🧠 Smart & Accurate SQL Generator (AI + Data-Aware NLP)
# =========================================================
def generate_sql(prompt_text, df):
    text = prompt_text.strip()
    lowered = text.lower()

    # 1. AI API Call (Open Mistral / LLM via GET)
    try:
        sys_info = f"Table: df, Columns: {list(df.columns)}, Sample: {df.head(2).to_dict(orient='records')}"
        encoded_prompt = urllib.parse.quote(
            f"Act as a DuckDB SQL generator. Only return the SQL query without any explanation or markdown formatting.\nContext: {sys_info}\nUser Question: {text}"
        )
        url = f"https://text.pollinations.ai/{encoded_prompt}?model=mistral"
        res = requests.get(url, timeout=8)
        if res.status_code == 200 and "SELECT" in res.text.upper():
            cleaned = res.text.strip().replace("```sql", "").replace("```", "").strip()
            match = re.search(r"(SELECT\s+.*)", cleaned, re.IGNORECASE | re.DOTALL)
            if match:
                test_sql = match.group(1).rstrip(";").strip()
                duckdb.query(test_sql).df()  # Validate execution
                return test_sql
    except Exception:
        pass

    # 2. Intelligent Data-Aware Parser (Guaranteed Fallback)
    cols = list(df.columns)
    cat_cols = [c for c in cols if not pd.api.types.is_numeric_dtype(df[c]) and c.lower() != 'date']
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]

    matched_filters = []
    for c in cat_cols:
        for val in df[c].dropna().unique():
            if str(val).lower() in lowered:
                matched_filters.append(f"LOWER({c}) = '{str(val).lower()}'")

    where_clause = f" WHERE {' AND '.join(matched_filters)}" if matched_filters else ""

    # Check grouping columns
    group_col = None
    for c in cat_cols:
        if c.lower() in lowered and not any(str(v).lower() in lowered for v in df[c].dropna().unique()):
            group_col = c
            break

    # Determine numeric metric
    num_col = "Sales" if "sales" in lowered and "Sales" in num_cols else (
        "Quantity" if "quantity" in lowered and "Quantity" in num_cols else (num_cols[0] if num_cols else None))

    if matched_filters and not group_col:
        display_cols = [c for c in cat_cols if not any(c in f for f in matched_filters)]
        target_group = display_cols[0] if display_cols else cat_cols[0]
        if num_col:
            return f"SELECT {target_group}, SUM({num_col}) AS Total_{num_col} FROM df{where_clause} GROUP BY {target_group}"
        return f"SELECT * FROM df{where_clause}"

    if group_col and num_col:
        return f"SELECT {group_col}, SUM({num_col}) AS Total_{num_col} FROM df{where_clause} GROUP BY {group_col}"

    if num_col and cat_cols:
        return f"SELECT {cat_cols[0]}, SUM({num_col}) AS Total_{num_col} FROM df GROUP BY {cat_cols[0]}"

    return "SELECT * FROM df LIMIT 10"


# Page Setup & Styling
st.set_page_config(
    page_title="Talk to Your Data | Text-to-SQL Engine",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #F8FAFC; }
    h1, h2, h3 { color: #0F172A; font-family: 'Space Grotesk', sans-serif; }
    .stButton>button { background-color: #2563EB; color: white; border-radius: 6px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Talk to Your Data — AI Analytics Engine")
st.write("Upload any CSV file, ask questions in plain English, and get instant SQL execution with dynamic charts.")

# Sidebar - File Ingestion
st.sidebar.header("📁 Data Ingestion")
uploaded_file = st.sidebar.file_uploader("Upload CSV Dataset", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.sidebar.success(f"Loaded {len(df)} rows successfully!")

    with st.expander("👀 View Raw Dataset Preview", expanded=False):
        st.dataframe(df.head(10), use_container_width=True)

    st.divider()

    user_query = st.text_input("💬 Ask a question about this data:",
                               placeholder="e.g., Show sales in Electronics category")

    if user_query:
        with st.spinner("🤖 Translating natural language to DuckDB SQL..."):
            try:
                sql_query = generate_sql(user_query, df)

                col_left, col_right = st.columns([1, 1])

                with col_left:
                    st.subheader("🔍 Generated SQL Query")
                    st.code(sql_query, language="sql")

                    result_df = duckdb.query(sql_query).df()
                    st.subheader("📋 Query Results")
                    st.dataframe(result_df, use_container_width=True)

                with col_right:
                    st.subheader("📈 Dynamic Visualization")
                    numeric_cols = [c for c in result_df.columns if pd.api.types.is_numeric_dtype(result_df[c])]
                    non_numeric_cols = [c for c in result_df.columns if not pd.api.types.is_numeric_dtype(result_df[c])]

                    if numeric_cols and non_numeric_cols:
                        fig = px.bar(
                            result_df,
                            x=non_numeric_cols[0],
                            y=numeric_cols[0],
                            title=f"{numeric_cols[0]} by {non_numeric_cols[0]}",
                            template="plotly_white",
                            color_discrete_sequence=['#2563EB']
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    elif len(numeric_cols) >= 2:
                        fig = px.bar(
                            result_df,
                            x=numeric_cols[0],
                            y=numeric_cols[1],
                            template="plotly_white",
                            color_discrete_sequence=['#2563EB']
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("ℹ️ Visualization rendered as table.")

            except Exception as e:
                st.error(f"❌ Execution Error: {e}")
else:
    st.info("👈 Upload `sales_data.csv` in the sidebar to get started!")