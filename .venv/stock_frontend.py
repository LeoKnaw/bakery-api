"""
Bakery Management System - New Streamlit Frontend
Run with: streamlit run stock_frontend.py --server.port 8502
"""

import streamlit as st
import requests
import api_client
from datetime import date, timedelta
import os
import time
from streamlit_cookies_manager import EncryptedCookieManager

st.set_page_config(page_title="Bakery Management", page_icon="🍞", layout="wide")

cookies = EncryptedCookieManager(
    prefix="bakery2/",
    password=os.environ.get("COOKIES_PASSWORD", "bakery-secret-2026"),
)
if not cookies.ready():
    st.spinner("Loading...")
    st.stop()

COOKIE_EXPIRY_SECONDS = 3600

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

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

    st.stop()


def show_admin_panel():
    if not st.session_state.is_admin:
        st.warning("Admin access required.")
        return

    st.header("👥 User Management")

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
    api_client.logout()
    for key in ["auth_token", "auth_time", "is_admin"]:
        if key in cookies:
            del cookies[key]
    cookies.save()
    st.session_state.authenticated = False
    st.session_state.is_admin = False
    st.rerun()


if not st.session_state.authenticated:
    show_login_page()

st.sidebar.title("🍞 Bakery")
st.sidebar.markdown(f"**Logged in** {'(Admin)' if st.session_state.is_admin else ''}")
if st.sidebar.button("Logout"):
    logout()
st.sidebar.markdown("---")

nav_options = ["Products", "Daily Stock"]
if st.session_state.is_admin:
    nav_options.append("👥 Admin")

page = st.sidebar.radio("Navigation", nav_options)


def show_products():
    st.header("Products")

    if "editing_product" not in st.session_state:
        st.session_state.editing_product = None

    with st.expander("Add New Product", expanded=False):
        with st.form("add_product", clear_on_submit=True):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                name = st.text_input("Product Name")
            with col2:
                price = st.number_input(
                    "Retail Price (₦)", min_value=50, step=50, format="%.2f"
                )
            with col3:
                wholesale_price = st.number_input(
                    "Wholesale Price (₦)", min_value=50, step=50, format="%.2f"
                )
            with col4:
                st.write("")
                st.write("")
                submitted = st.form_submit_button("Add Product")

            if submitted and name:
                try:
                    api_client.create_product(name, price, wholesale_price)
                    st.success(f"Added '{name}'!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    try:
        products = api_client.get_products()

        if not products:
            st.info("No products yet. Add your first product above!")
            return

        st.markdown("---")

        for product in products:
            if st.session_state.editing_product == product["id"]:
                with st.form(f"edit_form_{product['id']}"):
                    st.write(f"**Editing: {product['name']}**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        edit_name = st.text_input("Product Name", value=product["name"])
                    with col2:
                        edit_price = st.number_input(
                            "Retail Price (₦)",
                            min_value=50,
                            value=int(product["price"]),
                            step=50,
                            format="%.2f",
                        )
                    with col3:
                        edit_wholesale_price = st.number_input(
                            "Wholesale Price (₦)",
                            min_value=50,
                            value=int(product.get("wholesale_price", 0) or 0),
                            step=50,
                            format="%.2f",
                        )
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Save", type="primary"):
                            try:
                                api_client.update_product(
                                    product["id"], edit_name, edit_price, edit_wholesale_price
                                )
                                st.session_state.editing_product = None
                                st.success(f"Updated '{edit_name}'!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    with col2:
                        if st.form_submit_button("Cancel"):
                            st.session_state.editing_product = None
                            st.rerun()
            else:
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.write(f"**{product['name']}**")
                with col2:
                    st.write(f"₦{product['price']:,.2f}")
                with col3:
                    ws_price = product.get("wholesale_price")
                    if ws_price is not None:
                        st.write(f"WS: ₦{ws_price:,.2f}")
                    else:
                        st.write("WS: -")
                with col4:
                    if st.button("Edit", key=f"edit_{product['id']}"):
                        st.session_state.editing_product = product["id"]
                        st.rerun()

    except requests.ConnectionError:
        st.error(
            "Cannot connect to API. Make sure the FastAPI server is running on localhost:8000"
        )
    except Exception as e:
        st.error(f"Error: {e}")


def show_daily_stock():
    st.header("📊 Daily Stock Records")

    tab1, tab2, tab3 = st.tabs(
        ["📝 Create/Edit Records", "📋 View Records", "📈 Summary"]
    )

    with tab1:
        products = api_client.get_products()
        if not products:
            st.warning("No products available. Add products first!")
            return

        product_options = {p["id"]: p["name"] for p in products}
        product_prices = {p["id"]: p["price"] for p in products}
        product_ws_prices = {
            p["id"]: p.get("wholesale_price") or 0 for p in products
        }

        col1, col2 = st.columns([1, 3])
        with col1:
            record_date = st.date_input("Select Date", value=date.today())
        with col2:
            st.write("")
            st.write("")
            load_btn = st.button("Load/Start Records", type="primary")

        if load_btn:
            try:
                existing_records = api_client.get_daily_stock_records(
                    record_date=record_date.isoformat()
                )

                stock_data = []
                if existing_records:
                    stock_data = existing_records
                else:
                    created = api_client.create_daily_stock_records(
                        record_date.isoformat()
                    )
                    prev_date = record_date - timedelta(days=1)
                    prev_records = api_client.get_daily_stock_records(
                        record_date=prev_date.isoformat()
                    )
                    prev_closing_map = {
                        r["product_id"]: r["closing_stock"] for r in prev_records
                    }

                    stock_data = []
                    for rec in created:
                        prod_id = rec["product_id"]
                        stock_data.append(
                            {
                                "id": rec["id"],
                                "product_id": prod_id,
                                "opening_stock": prev_closing_map.get(prod_id, 0),
                                "production_stock": 0,
                                "wholesale_quantity": 0,
                                "retail_quantity": 0,
                                "supply_quantity": 0,
                                "wholesale_revenue": 0.0,
                                "retail_revenue": 0.0,
                                "closing_stock": prev_closing_map.get(prod_id, 0),
                            }
                        )

                st.session_state["stock_data"] = stock_data
                st.session_state["stock_date"] = record_date.isoformat()

            except Exception as e:
                st.error(f"Error loading records: {e}")

        if (
            "stock_data" in st.session_state
            and st.session_state.get("stock_date") == record_date.isoformat()
        ):
            stock_data = st.session_state["stock_data"]

            st.markdown("---")
            st.subheader(f"Records for {record_date}")

            header_cols = st.columns([2, 1, 1, 1, 1, 1, 1, 1, 1, 1])
            headers = [
                "Product",
                "Opening",
                "Production",
                "WS Qty",
                "RT Qty",
                "Supply",
                "WS Rev",
                "RT Rev",
                "Total Rev",
                "Closing",
            ]
            for col, h in zip(header_cols, headers):
                col.markdown(f"**{h}**")

            updated_data = []
            total_ws_rev = 0
            total_rt_rev = 0
            total_closing = 0

            for i, rec in enumerate(stock_data):
                prod_id = rec["product_id"]
                prod_name = product_options.get(prod_id, "Unknown")
                price = product_prices.get(prod_id, 0)
                ws_price = product_ws_prices.get(prod_id, 0)

                row_cols = st.columns([2, 1, 1, 1, 1, 1, 1, 1, 1, 1])

                with row_cols[0]:
                    st.write(f"**{prod_name}**")

                with row_cols[1]:
                    opening = st.number_input(
                        "Opening",
                        min_value=0,
                        value=rec["opening_stock"],
                        key=f"open_{i}",
                        label_visibility="collapsed",
                    )

                with row_cols[2]:
                    production = st.number_input(
                        "Production",
                        min_value=0,
                        value=rec["production_stock"],
                        key=f"prod_{i}",
                        label_visibility="collapsed",
                    )

                with row_cols[3]:
                    wholesale = st.number_input(
                        "WS",
                        min_value=0,
                        value=rec["wholesale_quantity"],
                        key=f"ws_{i}",
                        label_visibility="collapsed",
                    )

                with row_cols[4]:
                    retail = st.number_input(
                        "RT",
                        min_value=0,
                        value=rec["retail_quantity"],
                        key=f"rt_{i}",
                        label_visibility="collapsed",
                    )

                with row_cols[5]:
                    supply = st.number_input(
                        "Supply",
                        min_value=0,
                        value=rec.get("supply_quantity", 0),
                        key=f"supply_{i}",
                        label_visibility="collapsed",
                    )

                ws_rev = wholesale * ws_price
                rt_rev = retail * price
                total_rev = ws_rev + rt_rev
                closing = opening + production - wholesale - retail - supply

                with row_cols[6]:
                    st.write(f"₦{ws_rev:,.0f}")
                with row_cols[7]:
                    st.write(f"₦{rt_rev:,.0f}")
                with row_cols[8]:
                    st.write(f"₦{total_rev:,.0f}")
                with row_cols[9]:
                    st.write(f"**{closing}**")

                total_ws_rev += ws_rev
                total_rt_rev += rt_rev
                total_closing += closing

                updated_data.append(
                    {
                        "id": rec["id"],
                        "product_id": prod_id,
                        "opening_stock": opening,
                        "production_stock": production,
                        "wholesale_quantity": wholesale,
                        "retail_quantity": retail,
                        "supply_quantity": supply,
                        "wholesale_revenue": ws_rev,
                        "retail_revenue": rt_rev,
                        "closing_stock": closing,
                    }
                )

            st.markdown("---")
            summary_cols = st.columns(3)
            with summary_cols[0]:
                st.metric("Total WS Revenue", f"₦{total_ws_rev:,.0f}")
            with summary_cols[1]:
                st.metric("Total RT Revenue", f"₦{total_rt_rev:,.0f}")
            with summary_cols[2]:
                st.metric("Total Closing", total_closing)

            if st.button("Save All Records", type="primary"):
                try:
                    for rec in updated_data:
                        api_client.update_daily_stock_record(
                            rec["id"],
                            opening_stock=rec["opening_stock"],
                            production_stock=rec["production_stock"],
                            wholesale_quantity=rec["wholesale_quantity"],
                            retail_quantity=rec["retail_quantity"],
                            supply_quantity=rec["supply_quantity"],
                            wholesale_revenue=rec["wholesale_revenue"],
                            retail_revenue=rec["retail_revenue"],
                        )
                    st.toast("✅ Records saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")

    with tab2:
        st.subheader("View All Records")

        col1, col2, col3 = st.columns(3)
        with col1:
            view_start = st.date_input(
                "Start Date", value=date.today() - timedelta(days=7)
            )
        with col2:
            view_end = st.date_input("End Date", value=date.today())
        with col3:
            view_product = st.selectbox(
                "Product", options=["All"] + list(product_options.values()), index=0
            )

        if st.button("Load Records"):
            try:
                records = api_client.get_daily_stock_records(
                    start_date=view_start.isoformat(), end_date=view_end.isoformat()
                )

                if view_product != "All":
                    records = [
                        r
                        for r in records
                        if product_options.get(r["product_id"]) == view_product
                    ]

                if not records:
                    st.info("No records found")
                else:
                    import pandas as pd

                    df = pd.DataFrame(
                        [
                            {
                                "Date": r["record_date"],
                                "Product": product_options.get(
                                    r["product_id"], "Unknown"
                                ),
                                "Opening": r["opening_stock"],
                                "Production": r["production_stock"],
                                "Wholesale": r["wholesale_quantity"],
                                "Retail": r["retail_quantity"],
                                "Supply": r.get("supply_quantity", 0),
                                "Wholesale Rev": r["wholesale_revenue"],
                                "Retail Rev": r["retail_revenue"],
                                "Closing": r["closing_stock"],
                            }
                            for r in records
                        ]
                    )
                    st.dataframe(df, use_container_width=True)

            except Exception as e:
                st.error(f"Error: {e}")

    with tab3:
        st.subheader("Stock Summary Dashboard")

        col1, col2 = st.columns(2)
        with col1:
            sum_start = st.date_input(
                "Summary Start", value=date.today() - timedelta(days=30)
            )
        with col2:
            sum_end = st.date_input("Summary End", value=date.today())

        if st.button("Get Summary"):
            try:
                summary = api_client.get_stock_summary(
                    sum_start.isoformat(), sum_end.isoformat()
                )

                st.markdown("### 📊 Overall Totals")
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("Total Production", summary["totals"]["production_stock"])
                with col2:
                    st.metric("Wholesale Sold", summary["totals"]["wholesale_quantity"])
                with col3:
                    st.metric("Retail Sold", summary["totals"]["retail_quantity"])
                with col4:
                    st.metric("Supply", summary["totals"].get("supply_quantity", 0))
                with col5:
                    st.metric(
                        "Total Revenue", f"₦{summary['totals']['total_revenue']:,.0f}"
                    )

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Opening Stock", summary["totals"]["opening_stock"])
                with col2:
                    st.metric("Closing Stock", summary["totals"]["closing_stock"])
                with col3:
                    st.metric("Total Records", summary["total_records"])

                if summary.get("by_product"):
                    st.markdown("### 📦 By Product")
                    for prod in summary["by_product"]:
                        with st.expander(f"{prod['product_name']}"):
                            col1, col2, col3, col4, col5 = st.columns(5)
                            with col1:
                                st.metric("Production", prod["total_production"])
                            with col2:
                                st.metric("Wholesale", prod["total_wholesale"])
                            with col3:
                                st.metric("Retail", prod["total_retail"])
                            with col4:
                                st.metric("Supply", prod.get("total_supply", 0))
                            with col5:
                                st.metric("Revenue", f"₦{prod['total_revenue']:,.0f}")

            except Exception as e:
                st.error(f"Error: {e}")


if page == "Products":
    show_products()
elif page == "Daily Stock":
    show_daily_stock()
elif page == "👥 Admin":
    show_admin_panel()
