"""
Bakery Management System - Streamlit Frontend
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import requests
import api_client
from datetime import date

st.set_page_config(page_title="Bakery Management", page_icon="🍞", layout="wide")

# Sidebar navigation
st.sidebar.title("🍞 Bakery")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation", ["Products", "Record Production", "New Sale", "Inventory"]
)


def show_products():
    """Products page - view, add, edit, delete products."""
    st.header("Products")

    # Add new product form
    with st.expander("Add New Product", expanded=False):
        with st.form("add_product"):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                name = st.text_input("Product Name")
            with col2:
                price = st.number_input(
                    "Price ($)", min_value=0.01, step=0.01, format="%.2f"
                )
            with col3:
                st.write("")
                st.write("")
                submitted = st.form_submit_button("Add Product")

            if submitted and name:
                try:
                    api_client.create_product(name, price)
                    st.success(f"Added '{name}'!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # Display products
    try:
        products = api_client.get_products()

        if not products:
            st.info("No products yet. Add your first product above!")
            return

        # Create a table-like display
        st.markdown("---")

        for product in products:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.write(f"**{product['name']}**")
            with col2:
                st.write(f"₦{product['price']:.2f}")
            with col3:
                st.write(f"₦{product['wholesale_price']:.2f}")
            with col4:
                if st.button("Delete", key=f"del_{product['id']}"):
                    try:
                        api_client.delete_product(product["id"])
                        st.success("Deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    except requests.ConnectionError:
        st.error(
            "Cannot connect to API. Make sure the FastAPI server is running on localhost:8000"
        )
    except Exception as e:
        st.error(f"Error loading products: {e}")


def show_production():
    """Production page - record baking and view history."""
    st.header("Record Production")

    try:
        products = api_client.get_products()

        if not products:
            st.warning("No products available. Add products first!")
            return

        product_options = {p["id"]: p["name"] for p in products}

        # Record production form
        with st.form("record_production"):
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                selected_product = st.selectbox(
                    "Product",
                    options=list(product_options.keys()),
                    format_func=lambda x: product_options[x],
                )
            with col2:
                quantity = st.number_input("Quantity Produced", min_value=1, value=1)
            with col3:
                st.write("")
                st.write("")
                submitted = st.form_submit_button("Record")

            if submitted:
                try:
                    result = api_client.record_production(selected_product, quantity)
                    product_name = product_options[selected_product]
                    st.success(f"Recorded {quantity}x {product_name}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        # Show production history
        st.markdown("---")
        st.subheader("Recent Production")

        try:
            records = api_client.get_production_records()

            if not records:
                st.info("No production records yet.")
            else:
                for record in records:
                    col1, col2, col3 = st.columns([4, 2, 3])
                    with col1:
                        product_name = record.get("product", {}).get("name", "Unknown")
                        st.write(f"**{product_name}**")
                    with col2:
                        st.write(f"Qty: {record['quantity']}")
                    with col3:
                        timestamp = record.get("timestamp", "")
                        if timestamp:
                            st.write(timestamp[:16].replace("T", " "))

        except Exception as e:
            st.error(f"Error loading production history: {e}")

    except requests.ConnectionError:
        st.error(
            "Cannot connect to API. Make sure the FastAPI server is running on localhost:8000"
        )
    except Exception as e:
        st.error(f"Error: {e}")


def show_new_sale():
    """New Sale page - create a sale with multiple items."""
    st.header("New Sale")

    # Initialize session state for cart
    if "cart" not in st.session_state:
        st.session_state.cart = []

    try:
        products = api_client.get_products()

        if not products:
            st.warning("No products available. Add products first!")
            return

        # Product selection for adding to cart
        product_options = {
            p["id"]: f"{p['name']} (₦{p['price']:.2f})" for p in products
        }

        col1, col2, col3 = st.columns([4, 2, 1])
        with col1:
            selected_product = st.selectbox(
                "Select Product",
                options=list(product_options.keys()),
                format_func=lambda x: product_options[x],
            )
        with col2:
            quantity = st.number_input("Quantity", min_value=1, value=1)
        with col3:
            st.write("")
            st.write("")
            if st.button("Add to Cart"):
                # Check if product already in cart
                for item in st.session_state.cart:
                    if item["product_id"] == selected_product:
                        item["quantity"] += quantity
                        break
                else:
                    st.session_state.cart.append(
                        {"product_id": selected_product, "quantity": quantity}
                    )
                st.rerun()

        # Display cart
        st.markdown("---")
        st.subheader("Cart")

        if not st.session_state.cart:
            st.info("Cart is empty. Add items above.")
        else:
            total = 0
            for i, item in enumerate(st.session_state.cart):
                product = next(
                    (p for p in products if p["id"] == item["product_id"]), None
                )
                if product:
                    qty = item["quantity"]
                    if qty > 5:
                        item_total = product["wholesale_price"] * qty
                    else:
                        item_total = product["price"] * qty
                    total += item_total

                    col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
                    with col1:
                        st.write(product["name"])
                    with col2:
                        st.write(f"Qty: {item['quantity']}")
                    with col3:
                        st.write(f"${item_total:.2f}")
                    with col4:
                        if st.button("Remove", key=f"remove_{i}"):
                            st.session_state.cart.pop(i)
                            st.rerun()

            st.markdown("---")
            st.markdown(f"### Total: ${total:.2f}")

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Clear Cart", type="secondary"):
                    st.session_state.cart = []
                    st.rerun()
            with col2:
                if st.button("Complete Sale", type="primary"):
                    try:
                        result = api_client.create_sale(st.session_state.cart)
                        st.success(f"Sale completed! Sale ID: {result['sale_id']}")
                        st.session_state.cart = []
                        st.rerun()
                    except Exception as e:
                        error_msg = str(e).replace("\n", "<br>")
                        st.error(f"**Error completing sale:**   {error_msg}")

    except requests.ConnectionError:
        st.error(
            "Cannot connect to API. Make sure the FastAPI server is running on localhost:8000"
        )
    except Exception as e:
        st.error(f"Error: {e}")


def show_inventory():
    """Inventory page - check stock levels for products."""
    st.header("Inventory")

    try:
        products = api_client.get_products()

        if not products:
            st.warning("No products available. Add products first!")
            return

        product_options = {p["id"]: p["name"] for p in products}

        selected_product = st.selectbox(
            "Select Product",
            options=list(product_options.keys()),
            format_func=lambda x: product_options[x],
        )

        col1, col2 = st.columns([2, 2])
        with col1:
            check_date = st.date_input("Date", value=date.today())

        if st.button("Check Inventory"):
            try:
                inventory = api_client.get_inventory(
                    selected_product, for_date=check_date.isoformat()
                )

                st.markdown("---")
                st.subheader(f"Inventory: {inventory['product_name']}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Opening Stock", inventory["opening_stock"])
                with col2:
                    st.metric("Produced Today", inventory["production_stock"])
                with col3:
                    st.metric("Sold Today", inventory["sales_stock"])

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Closing Stock", inventory["closing_stock"])
                with col2:
                    st.metric("Current Stock", inventory["current_stock"])

            except Exception as e:
                st.error(f"Error fetching inventory: {e}")

    except requests.ConnectionError:
        st.error(
            "Cannot connect to API. Make sure the FastAPI server is running on localhost:8000"
        )
    except Exception as e:
        st.error(f"Error: {e}")


# Page router
if page == "Products":
    show_products()
elif page == "Record Production":
    show_production()
elif page == "New Sale":
    show_new_sale()
elif page == "Inventory":
    show_inventory()
