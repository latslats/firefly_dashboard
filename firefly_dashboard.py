import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
from dateutil import parser

# Custom date parsing function
def parse_date(date_string):
    try:
        return parser.parse(date_string).replace(tzinfo=None)
    except:
        return pd.NaT

# Data loading and preprocessing
@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    
    df['date'] = df['date'].apply(parse_date)
    df = df.dropna(subset=['date'])
    df['month'] = df['date'].dt.to_period('M').astype(str)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').abs()
    df['category'] = df['category'].fillna('Uncategorized')
    
    return df

# Create bar charts
def create_bar_charts(df, selected_categories, start_date, end_date):
    mask = (
        df['category'].isin(selected_categories) &
        (df['date'].dt.date >= start_date) &
        (df['date'].dt.date <= end_date)
    )
    filtered_df = df[mask]
    
    income_df = filtered_df[filtered_df['type'] == 'Deposit']
    expense_df = filtered_df[filtered_df['type'] == 'Withdrawal']
    
    fig = make_subplots(rows=2, cols=1, subplot_titles=("Income per Category per Month", "Expenses per Category per Month"))
    
    income_grouped = income_df.groupby(['month', 'category'])['amount'].sum().reset_index()
    income_chart = px.bar(income_grouped, x='month', y='amount', color='category', title='Income')
    for trace in income_chart.data:
        fig.add_trace(trace, row=1, col=1)
    
    expense_grouped = expense_df.groupby(['month', 'category'])['amount'].sum().reset_index()
    expense_grouped = expense_grouped.sort_values(['month', 'amount'], ascending=[True, False])
    expense_chart = px.bar(expense_grouped, x='month', y='amount', color='category', title='Expenses')
    for trace in expense_chart.data:
        fig.add_trace(trace, row=2, col=1)
    
    fig.update_layout(height=1000, title_text="Income and Expenses per Category per Month")
    return fig

# Create pie chart for monthly expenses
def create_expense_pie_chart(df, selected_categories, selected_month):
    mask = (
        df['category'].isin(selected_categories) &
        (df['month'] == selected_month) &
        (df['type'] == 'Withdrawal')
    )
    filtered_df = df[mask]
    
    grouped_df = filtered_df.groupby('category')['amount'].sum().reset_index()
    grouped_df = grouped_df.sort_values('amount', ascending=False)
    fig = px.pie(grouped_df, values='amount', names='category', title=f'Expense Distribution for {selected_month}')
    return fig

# Main Streamlit app
def main():
    st.title('Firefly 3 Finance Dashboard')

    try:
        data = load_data("firefly_export.csv")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    st.sidebar.header('Filters')

    # Category selection with "Select All" button
    categories = sorted(data['category'].unique())
    selected_categories = st.sidebar.multiselect('Select Categories', categories, default=categories[:5])
    
    if st.sidebar.button('Select All Categories'):
        selected_categories = categories
        st.sidebar.write("All categories selected!")

    min_date = data['date'].min().date()
    max_date = data['date'].max().date()
    start_date = st.sidebar.date_input('Start Date', min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input('End Date', max_date, min_value=min_date, max_value=max_date)

    # Month selection for pie chart
    available_months = sorted(data['month'].unique())
    selected_month = st.sidebar.selectbox('Select Month for Expense Pie Chart', available_months, index=len(available_months)-1)

    if selected_categories:
        st.header('Income and Expenses Over Time')
        charts = create_bar_charts(data, selected_categories, start_date, end_date)
        st.plotly_chart(charts)

        st.header('Monthly Expense Distribution')
        pie_chart = create_expense_pie_chart(data, selected_categories, selected_month)
        st.plotly_chart(pie_chart)
    else:
        st.warning('Please select at least one category.')

    st.header('Financial Summary')
    summary_data = data[
        data['category'].isin(selected_categories) & 
        (data['date'].dt.date >= start_date) & 
        (data['date'].dt.date <= end_date)
    ]
    
    st.subheader('Income Summary')
    income_summary = summary_data[summary_data['type'] == 'Deposit'].groupby('category')['amount'].agg(['sum', 'mean', 'count']).round(2)
    income_summary.columns = ['Total Amount', 'Average Amount', 'Number of Transactions']
    income_summary = income_summary.sort_values('Total Amount', ascending=False)
    st.dataframe(income_summary)
    
    st.subheader('Expense Summary')
    expense_summary = summary_data[summary_data['type'] == 'Withdrawal'].groupby('category')['amount'].agg(['sum', 'mean', 'count']).round(2)
    expense_summary.columns = ['Total Amount', 'Average Amount', 'Number of Transactions']
    expense_summary = expense_summary.sort_values('Total Amount', ascending=False)
    st.dataframe(expense_summary)

if __name__ == "__main__":
    main()