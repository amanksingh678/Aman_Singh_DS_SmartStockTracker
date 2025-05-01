import streamlit as st
import plotly.express as px
from utils.db_manager import DatabaseManager
import pandas as pd

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseManager()

# Page config
st.set_page_config(
    page_title="Inventory Management System",
    page_icon="📦",
    layout="wide"
)

# Load custom CSS
with open('assets/custom.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def main():
    st.title("📊 Dashboard")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    products_df = st.session_state.db.get_products()
    transactions_df = st.session_state.db.get_transactions()
    
    with col1:
        st.metric("Total Products", len(products_df))
    with col2:
        st.metric("Total Stock", products_df['quantity'].sum())
    with col3:
        st.metric("Total Value", f"${(products_df['quantity'] * products_df['price']).sum():,.2f}")
    with col4:
        low_stock = len(st.session_state.db.get_low_stock_alerts())
        st.metric("Low Stock Alerts", low_stock)

    # Create two columns for charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Inventory Distribution")
        fig = px.pie(products_df, values='quantity', names='name',
                     title='Current Inventory Distribution')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Product Value Distribution")
        product_values = products_df['quantity'] * products_df['price']
        fig = px.bar(products_df, x='name', y=product_values,
                     title='Product Value Distribution')
        st.plotly_chart(fig, use_container_width=True)

    # Low stock alerts
    st.subheader("Low Stock Alerts")
    alerts = st.session_state.db.get_low_stock_alerts()
    if not alerts.empty:
        for _, alert in alerts.iterrows():
            st.warning(f"Low stock alert for {alert['name']}: {alert['quantity']} units remaining")
    else:
        st.success("No low stock alerts")

if __name__ == "__main__":
    main()
