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
    try:
        mask = (
            df['category'].isin(selected_categories) &
            (df['date'].dt.date >= start_date) &
            (df['date'].dt.date <= end_date)
        )
        filtered_df = df[mask]
        
        if filtered_df.empty:
            return None
        
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
    except Exception as e:
        st.error(f"Error creating bar charts: {e}")
        return None

# Create pie chart for monthly expenses
def create_expense_pie_chart(df, selected_categories, start_date, end_date, threshold):
    try:
        mask = (
            df['category'].isin(selected_categories) &
            (df['date'].dt.date >= start_date) &
            (df['date'].dt.date <= end_date) &
            (df['type'] == 'Withdrawal')
        )
        filtered_df = df[mask]
        
        if filtered_df.empty:
            return None
        
        grouped_df = filtered_df.groupby('category')['amount'].sum().reset_index()
        grouped_df = grouped_df.sort_values('amount', ascending=False)
        total_amount = grouped_df['amount'].sum()
        grouped_df['percentage'] = (grouped_df['amount'] / total_amount) * 100
        grouped_df = grouped_df[grouped_df['percentage'] >= threshold]
        fig = px.pie(grouped_df, values='amount', names='category', title=f'Expense Distribution from {start_date} to {end_date}', hover_data=['category'])
        return fig
    except Exception as e:
        st.error(f"Error creating pie chart: {e}")
        return None

# New function for income vs expenses overview
def create_overview(df, start_date, end_date):
    mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
    filtered_df = df[mask]
    
    total_income = filtered_df[filtered_df['type'] == 'Deposit']['amount'].sum()
    total_expenses = filtered_df[filtered_df['type'] == 'Withdrawal']['amount'].sum()
    net_savings = total_income - total_expenses
    
    return total_income, total_expenses, net_savings

# New function for time series trend
def create_time_series(df, start_date, end_date):
    try:
        mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
        filtered_df = df[mask]
        
        if filtered_df.empty:
            return None
        
        daily_summary = filtered_df.groupby(['date', 'type'])['amount'].sum().unstack(fill_value=0).reset_index()
        daily_summary['Net'] = daily_summary['Deposit'] - daily_summary['Withdrawal']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily_summary['date'], y=daily_summary['Deposit'], name='Income', line=dict(color='green')))
        fig.add_trace(go.Scatter(x=daily_summary['date'], y=daily_summary['Withdrawal'], name='Expenses', line=dict(color='red')))
        fig.add_trace(go.Scatter(x=daily_summary['date'], y=daily_summary['Net'], name='Net', line=dict(color='blue')))
        
        fig.update_layout(title='Income vs Expenses Over Time', xaxis_title='Date', yaxis_title='Amount')
        return fig
    except Exception as e:
        st.error(f"Error creating time series chart: {e}")
        return None

# Updated function for top N categories
def get_top_categories(df, category_type, n, start_date, end_date, selected_categories):
    mask = (
        (df['date'].dt.date >= start_date) & 
        (df['date'].dt.date <= end_date) &
        (df['category'].isin(selected_categories))
    )
    filtered_df = df[mask]
    
    if category_type == 'Income':
        data = filtered_df[filtered_df['type'] == 'Deposit']
    else:
        data = filtered_df[filtered_df['type'] == 'Withdrawal']
    
    top_categories = data.groupby('category')['amount'].sum().nlargest(n).reset_index()
    return top_categories

# New function to get transactions for a specific category and month
def get_transactions(df, category, month):
    mask = (df['category'] == category) & (df['month'] == month)
    transactions = df[mask].sort_values('date', ascending=False)
    return transactions[['date', 'description', 'amount', 'type']]

# Main Streamlit app
def main():
    st.title('Firefly 3 Finance Dashboard')

    with st.spinner('Loading data...'):
        try:
            data = load_data("firefly_export.csv")
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return

    # Create tabs
    tab1, tab2 = st.tabs(["Dashboard", "Transaction Details"])

    with tab1:
        st.header('Financial Dashboard')

        st.sidebar.header('Filters')

        # Category selection with "Select All" button
        categories = sorted(data['category'].unique())
        
        if 'selected_categories' not in st.session_state:
            st.session_state.selected_categories = categories[:5]
        
        if st.sidebar.button('Select All Categories'):
            st.session_state.selected_categories = categories
        
        selected_categories = st.sidebar.multiselect('Select Categories', categories, default=st.session_state.selected_categories)

        min_date = data['date'].min().date()
        max_date = data['date'].max().date()
        
        # Date range selector
        date_range = st.sidebar.date_input(
            "Select Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = end_date = date_range

        # Threshold slider for pie chart
        threshold = st.sidebar.slider('Minimum Percentage to Show on Pie Chart', 0.0, 5.0, 0.5, 0.5)
        available_months = sorted(data['month'].unique())

        # Overview section
        st.subheader('Financial Overview')
        total_income, total_expenses, net_savings = create_overview(data, start_date, end_date)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"${total_income:.2f}")
        col2.metric("Total Expenses", f"${total_expenses:.2f}")
        col3.metric("Net Savings", f"${net_savings:.2f}", delta=f"${net_savings:.2f}")

        # Charts in tabs
        chart_tab1, chart_tab2, chart_tab3 = st.tabs(["Time Series", "Bar Charts", "Pie Chart"])

        with chart_tab1:
            st.subheader('Income vs Expenses Over Time')
            time_series_chart = create_time_series(data, start_date, end_date)
            if time_series_chart:
                st.plotly_chart(time_series_chart)
            else:
                st.warning("No data available for the selected date range.")

        with chart_tab2:
            if selected_categories:
                st.subheader('Income and Expenses by Category')
                charts = create_bar_charts(data, selected_categories, start_date, end_date)
                if charts:
                    st.plotly_chart(charts)
                else:
                    st.warning("No data available for the selected categories and date range.")
            else:
                st.warning('Please select at least one category.')

        with chart_tab3:
            if selected_categories:
                st.subheader('Monthly Expense Distribution')
                pie_chart = create_expense_pie_chart(data, selected_categories, start_date, end_date, threshold)
                if pie_chart:
                    st.plotly_chart(pie_chart)
                else:
                    st.warning("No expense data available for the selected categories and date range.")
            else:
                st.warning('Please select at least one category.')

        # Top N categories
        st.subheader('Top Categories')
        n = st.slider('Select number of top categories to display', 3, 10, 5)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f'Top {n} Income Sources')
            top_income = get_top_categories(data, 'Income', n, start_date, end_date, selected_categories)
            st.dataframe(top_income)
        with col2:
            st.subheader(f'Top {n} Expense Categories')
            top_expenses = get_top_categories(data, 'Expenses', n, start_date, end_date, selected_categories)
            st.dataframe(top_expenses)

        # Existing summary tables
        with st.expander("Detailed Financial Summary"):
            st.subheader('Income Summary')
            income_summary = data[(data['type'] == 'Deposit') & (data['category'].isin(selected_categories)) & (data['date'].dt.date >= start_date) & (data['date'].dt.date <= end_date)].groupby('category')['amount'].agg(['sum', 'count']).round(2)
            income_summary.columns = ['Total Amount', 'Number of Transactions']
            total_income_amount = income_summary['Total Amount'].sum()
            num_months = ((end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1)
            income_summary['Average Amount'] = (income_summary['Total Amount'] / num_months).round(2)
            income_summary['% of Total'] = (income_summary['Total Amount'] / total_income_amount * 100).round(2)
            income_summary = income_summary.sort_values('Total Amount', ascending=False)
            st.dataframe(income_summary)
            
            st.subheader('Expense Summary')
            expense_summary = data[(data['type'] == 'Withdrawal') & (data['category'].isin(selected_categories)) & (data['date'].dt.date >= start_date) & (data['date'].dt.date <= end_date)].groupby('category')['amount'].agg(['sum', 'count']).round(2)
            expense_summary.columns = ['Total Amount', 'Number of Transactions']
            total_expense_amount = expense_summary['Total Amount'].sum()
            expense_summary['Average Amount'] = (expense_summary['Total Amount'] / num_months).round(2)
            expense_summary['% of Total'] = (expense_summary['Total Amount'] / total_expense_amount * 100).round(2)
            expense_summary = expense_summary.sort_values('Total Amount', ascending=False)
            st.dataframe(expense_summary)

    with tab2:
        st.header('Transaction Details')
        
        # Category and month selection for transaction details
        selected_category = st.selectbox('Select Category', ['All'] + list(categories))
        selected_month_transactions = st.selectbox('Select Month', available_months, index=len(available_months)-1)
        
        # Search functionality
        search_term = st.text_input("Search transactions")
        
        # Get and display transactions
        if selected_category == 'All':
            transactions = get_transactions(data, data['category'], selected_month_transactions)
        else:
            transactions = get_transactions(data, selected_category, selected_month_transactions)
        
        if search_term:
            transactions = transactions[transactions['description'].str.contains(search_term, case=False)]
        
        if transactions.empty:
            st.warning("No transactions found for the selected criteria.")
        else:
            st.subheader(f'Transactions for {selected_category} in {selected_month_transactions}')
            st.dataframe(transactions, use_container_width=True)

            # Download button for transactions
            csv = transactions.to_csv(index=False)
            st.download_button(
                label="Download transactions as CSV",
                data=csv,
                file_name=f"transactions_{selected_category}_{selected_month_transactions}.csv",
                mime="text/csv",
            )

            # Summary statistics for selected transactions
            st.subheader('Summary Statistics')
            total_amount = transactions['amount'].sum()
            avg_amount = transactions['amount'].mean()
            num_transactions = len(transactions)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Amount", f"${total_amount:.2f}")
            col2.metric("Average Amount", f"${avg_amount:.2f}")
            col3.metric("Number of Transactions", num_transactions)

if __name__ == "__main__":
    main()