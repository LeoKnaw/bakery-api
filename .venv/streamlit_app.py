"""
Bakery Management System - Streamlit Frontend
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import requests
import api_client
from datetime import date
import os
import time
from streamlit_cookies_manager import EncryptedCookieManager

st.set_page_config(page_title="Bakery Management", page_icon="🍞", layout="wide")

# Initialize encrypted cookie manager
cookies = EncryptedCookieManager(
    prefix="bakery/",
    password=os.environ.get("COOKIES_PASSWORD", "bakery-secret-2026"),
)
if not cookies.ready():
    st.spinner("Loading...")
    st.stop()

COOKIE_EXPIRY_SECONDS = 3600  # 1 hour

# Initialize auth state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# Restore auth from cookie with expiration check
if not st.session_state.authenticated:
    auth_token = cookies.get("auth_token")
    auth_time = cookies.get("auth_time")

    if auth_token and auth_time:
        try:
            elapsed = time.time() - float(auth_time)
            if elapsed < COOKIE_EXPIRY_SECONDS:
                st.session_state.authenticated = True
                st.session_state.is_admin = (
                    cookies.get("is_admin", "false").lower() == "true"
                )
                api_client.set_user_token(auth_token, st.session_state.is_admin)
            else:
                for key in ["auth_token", "auth_time", "is_admin"]:
                    if key in cookies:
                        del cookies[key]
                cookies.save()
        except (ValueError, TypeError):
            for key in ["auth_token", "auth_time", "is_admin"]:
                if key in cookies:
                    del cookies[key]
            cookies.save()


def show_login_page():
    """Display login and registration page."""
    st.title("🍞 Bakery Management")
    st.markdown("---")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                try:
                    result = api_client.login(username, password)
                    st.session_state.authenticated = True
                    st.session_state.is_admin = result["is_admin"]
                    cookies["auth_token"] = result["access_token"]
                    cookies["is_admin"] = str(result["is_admin"])
                    cookies["auth_time"] = str(time.time())
                    cookies.save()
                    st.success("Login successful!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

    with tab2:
        st.subheader("Register")
        st.info("After registration, wait for admin approval.")
        with st.form("register_form"):
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Register")

            if submitted:
                if new_password != confirm_password:
                    st.error("Passwords don't match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    try:
                        api_client.register(new_username, new_password)
                        st.success("Registration successful! Wait for admin approval.")
                    except Exception as e:
                        st.error(f"Registration failed: {e}")

    st.stop()  # Stop here until authenticated


def show_admin_panel():
    """Display admin panel for user management."""
    if not st.session_state.is_admin:
        st.warning("Admin access required.")
        return

    st.header("👥 User Management")

    # Pending users
    st.subheader("Pending Approvals")
    try:
        pending = api_client.get_pending_users()
        if pending:
            for user in pending:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(
                        f"**{user['username']}** - Registered: {user['created_at'][:10]}"
                    )
                with col2:
                    if st.button("Approve", key=f"approve_{user['id']}"):
                        api_client.approve_user(user["id"])
                        st.success(f"Approved {user['username']}")
                        st.rerun()
        else:
            st.info("No pending users")
    except Exception as e:
        st.error(f"Error loading users: {e}")

    # All users
    st.subheader("All Users")
    try:
        users = api_client.get_all_users()
        for user in users:
            status = (
                "✓ Admin"
                if user["is_admin"]
                else ("✓ Approved" if user["is_approved"] else "⏳ Pending")
            )
            st.write(f"**{user['username']}** - {status}")
    except Exception as e:
        st.error(f"Error loading users: {e}")


def logout():
    """Handle logout."""
    api_client.logout()
    for key in ["auth_token", "auth_time", "is_admin"]:
        if key in cookies:
            del cookies[key]
    cookies.save()
    st.session_state.authenticated = False
    st.session_state.is_admin = False
    st.rerun()


# Check authentication
if not st.session_state.authenticated:
    show_login_page()

# Sidebar navigation with logout
st.sidebar.title("🍞 Bakery")
st.sidebar.markdown(f"**Logged in** {'(Admin)' if st.session_state.is_admin else ''}")
if st.sidebar.button("Logout"):
    logout()
st.sidebar.markdown("---")

# Build navigation options
nav_options = ["Products", "Record Production", "New Sale", "Inventory"]
if st.session_state.is_admin:
    nav_options.append("👥 Admin")

page = st.sidebar.radio("Navigation", nav_options)


def show_products():
    """Products page - view, add, edit, delete products."""
    st.header("Products")

    # Initialize session state for editing
    if "editing_product" not in st.session_state:
        st.session_state.editing_product = None

    # Add new product form
    with st.expander("Add New Product", expanded=False):
        with st.form("add_product", clear_on_submit=True):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                name = st.text_input("Product Name")
            with col2:
                price = st.number_input(
                    "Price (₦)", min_value=50, step=50, format="%.2f"
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
            # Show edit form if this product is being edited
            if st.session_state.editing_product == product["id"]:
                with st.form(f"edit_form_{product['id']}"):
                    st.write(f"**Editing: {product['name']}**")
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_name = st.text_input("Product Name", value=product["name"])
                    with col2:
                        edit_price = st.number_input(
                            "Price (₦)",
                            min_value=50,
                            value=int(product["price"]),
                            step=50,
                            format="%.2f",
                        )
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Save", type="primary"):
                            try:
                                api_client.update_product(
                                    product["id"], edit_name, edit_price
                                )
                                st.success("Product updated!")
                                st.session_state.editing_product = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    with col2:
                        if st.form_submit_button("Cancel"):
                            st.session_state.editing_product = None
                            st.rerun()
            else:
                # Normal product display
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
                with col1:
                    st.write(f"**{product['name']}**")
                with col2:
                    st.write(f"₦{product['price']:.2f}")
                with col3:
                    st.write(f"₦{product['wholesale_price']:.2f}")
                with col4:
                    if st.button("Edit", key=f"edit_{product['id']}"):
                        st.session_state.editing_product = product["id"]
                        st.rerun()
                with col5:
                    if st.button("Deactivate", key=f"del_{product['id']}"):
                        try:
                            api_client.deactivate_product(product["id"])
                            st.success("Deactivated!")
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

        col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
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
            is_supply = st.checkbox("Supply")
        with col4:
            st.write("")
            st.write("")
            if st.button("Add to Cart"):
                if is_supply:
                    sale_type = "supply"
                elif quantity >= 5:
                    sale_type = "wholesale"
                else:
                    sale_type = "retail"
                # Check if product already in cart with same sale_type
                for item in st.session_state.cart:
                    if (
                        item["product_id"] == selected_product
                        and item.get("sale_type") == sale_type
                    ):
                        item["quantity"] += quantity
                        break
                else:
                    st.session_state.cart.append(
                        {
                            "product_id": selected_product,
                            "quantity": quantity,
                            "sale_type": sale_type,
                        }
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
                    sale_type = item.get("sale_type", "retail")

                    # Supply items have no price
                    if sale_type == "supply":
                        item_total = 0
                    elif qty >= 5:
                        item_total = product["wholesale_price"] * qty
                    else:
                        item_total = product["price"] * qty
                    total += item_total

                    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                    with col1:
                        st.write(product["name"])
                    with col2:
                        st.write(f"Qty: {item['quantity']}")
                    with col3:
                        if sale_type == "supply":
                            st.write("Supply")
                        else:
                            st.write("")
                    with col4:
                        st.write(f"₦{item_total:.2f}")
                    with col5:
                        if st.button("Remove", key=f"remove_{i}"):
                            st.session_state.cart.pop(i)
                            st.rerun()

            st.markdown("---")
            st.markdown(f"### Total: ₦{total:.2f}")

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
elif page == "👥 Admin":
    show_admin_panel()
