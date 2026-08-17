import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
import re


# =========================================================
# 🧠 Deterministic & Accurate Text-to-SQL Engine
# =========================================================
def generate_sql(prompt_text, df):
    text = prompt_text.strip()
    lowered = text.lower()
    cols = list(df.columns)

    cat_cols = [c for c in cols if not pd.api.types.is_numeric_dtype(df[c]) and c.lower() != 'date']
    num_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]

    # 1. Detect Exact Column Value Filters (e.g., North, Electronics, Laptop)
    matched_filters = []
    filtered_cols = set()
    for c in cat_cols:
        for val in df[c].dropna().unique():
            # Exact word or phrase match
            if re.search(rf"\b{re.escape(str(val).lower())}\b", lowered):
                matched_filters.append(f"LOWER({c}) = '{str(val).lower()}'")
                filtered_cols.add(c)

    where_clause = f" WHERE {' AND '.join(matched_filters)}" if matched_filters else ""

    # 2. Detect Target Metric (Sales vs Quantity vs Count)
    is_qty = any(w in lowered for w in ["quantity", "qty", "number", "count", "items", "units", "total product"])
    is_sales = any(w in lowered for w in ["sales", "revenue", "amount", "price", "earning"])

    target_num = None
    if is_qty and "Quantity" in num_cols:
        target_num = "Quantity"
    elif is_sales and "Sales" in num_cols:
        target_num = "Sales"
    elif num_cols:
        target_num = num_cols[0]

    # 3. Detect Group By Column
    group_col = None
    for c in cat_cols:
        if c not in filtered_cols and (
                c.lower() in lowered or f"by {c.lower()}" in lowered or f"per {c.lower()}" in lowered):
            group_col = c
            break

    # If "product" explicitly mentioned with grouping intent, group by Product
    if "product" in lowered and "Product" not in filtered_cols:
        group_col = "Product"

    # 4. Formulate Accurate SQL Query
    if group_col and target_num:
        return f"SELECT {group_col}, SUM({target_num}) AS Total_{target_num} FROM df{where_clause} GROUP BY {group_col}"

    if target_num and where_clause and not group_col:
        return f"SELECT SUM({target_num}) AS Total_{target_num} FROM df{where_clause}"

    if group_col:
        return f"SELECT {group_col}, COUNT(*) AS Count FROM df{where_clause} GROUP BY {group_col}"

    if where_clause:
        return f"SELECT * FROM df{where_clause}"

    # Default Top Overview
    primary_cat = cat_cols[0] if cat_cols else cols[0]
    primary_num = num_cols[0] if num_cols else cols[-1]
    return f"SELECT {primary_cat}, SUM({primary_num}) AS Total_{primary_num} FROM df GROUP BY {primary_cat}"


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
                               placeholder="e.g., total number of product in north region")

    if user_query:
        with st.spinner("⚡ Translating to SQL and executing..."):
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
                    else:
                        st.info("ℹ️ Single metric scalar output; table view shown on the left.")

            except Exception as e:
                st.error(f"❌ Execution Error: {e}")
else:
    st.info("👈 Upload `sales_data.csv` in the sidebar to get started!")