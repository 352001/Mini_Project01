import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import mysql.connector

# ---------------- SAFE RERUN WRAPPER ----------------
def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        try:
            qp = dict(st.query_params)
            qp["_rnd"] = [str(datetime.now().timestamp())]
            st.set_query_params(**qp)
        except Exception:
            pass

# --- Sidebar / Title ---
side = st.sidebar.radio('Select user', ['Home', 'Client', 'Support'])
st.title("**Client Query Analysis System**")

# --- MySQL connection (adjust credentials as needed) ---
mydb = mysql.connector.connect(
    host="localhost",
    user="Customer_queries",
    password="Support",
    database="customer_queries",
    autocommit=True,
    auth_plugin='mysql_native_password'
)
mycursor = mydb.cursor(buffered=True)

# ---------------- Helper DB functions ----------------
def is_query_id_auto_increment():
    """
    Return True if query_id column has AUTO_INCREMENT in 'Extra', False otherwise.
    On error, assume False (so app computes an id).
    """
    try:
        cur = mydb.cursor()
        cur.execute("SHOW COLUMNS FROM customer_data LIKE 'query_id'")
        row = cur.fetchone()
        cur.close()
        if row and len(row) >= 6:
            # SHOW COLUMNS returns: Field, Type, Null, Key, Default, Extra
            extra = row[5] or ""
            return "auto_increment" in extra.lower()
        return False
    except Exception:
        return False

def get_next_query_id():
    """
    Returns next query_id to use if the column is NOT auto_increment.
    Uses MAX(query_id)+1. If table empty, returns 1.
    """
    try:
        cur = mydb.cursor()
        cur.execute("SELECT COALESCE(MAX(query_id), 0) + 1 FROM customer_data")
        nxt = cur.fetchone()[0]
        cur.close()
        return int(nxt)
    except Exception:
        # fallback: timestamp-based integer (should rarely be used)
        return int(datetime.now().timestamp())

def fetch_open_complaints(email_val, mobile_val):
    cur = mydb.cursor()
    sql = """
        SELECT query_id, name, email, mobile, query_heading, query_description, status, created_at, closed_at, remarks
        FROM customer_data
        WHERE (email = %s OR mobile = %s)
          AND COALESCE(status, '') = 'open'
        ORDER BY created_at DESC, query_id DESC
    """
    cur.execute(sql, (email_val, mobile_val))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    cur.close()
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows, columns=cols)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce").dt.strftime("%d-%m-%Y %H:%M:%S").fillna("")
    if "closed_at" in df.columns:
        df["closed_at"] = pd.to_datetime(df["closed_at"], errors="coerce").dt.strftime("%d-%m-%Y %H:%M:%S").fillna("")
    if "remarks" in df.columns:
        df["remarks"] = df["remarks"].fillna("")
    return df

def fetch_complaints_lookup(name_val=None, email_val=None, mobile_val=None, status_filter=None):
    """
    Build SQL dynamically so missing filters mean 'don't filter by that column'.
    """
    cur = mydb.cursor()
    base_sql = """
        SELECT query_id, name, email, mobile, query_heading, query_description, status, created_at, closed_at, remarks
        FROM customer_data
        WHERE 1=1
    """
    params = []

    # Add filters only when provided and non-empty
    if name_val:
        base_sql += " AND name = %s"
        params.append(name_val)
    if email_val:
        base_sql += " AND email = %s"
        params.append(email_val)
    if mobile_val:
        base_sql += " AND mobile = %s"
        params.append(mobile_val)

    if status_filter and status_filter != "all":
        base_sql += " AND COALESCE(status, '') = %s"
        params.append(status_filter)

    base_sql += " ORDER BY created_at DESC, query_id DESC"
    cur.execute(base_sql, tuple(params))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    cur.close()
    if not rows:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(rows, columns=cols)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce").dt.strftime("%d-%m-%Y %H:%M:%S").fillna("")
    if "closed_at" in df.columns:
        df["closed_at"] = pd.to_datetime(df["closed_at"], errors="coerce").dt.strftime("%d-%m-%Y %H:%M:%S").fillna("")
    if "remarks" in df.columns:
        df["remarks"] = df["remarks"].fillna("")
    return df

# ---------------- Client side ----------------
if side == 'Client':
    st.title("Customer Queries Dashboard")

    # --- static client users (demo) ---
    users = {
        "selva": {"password": "1111", "email": "selva@gmail.com", "mobile": "9000000001"},
        "sri":  {"password": "2222", "email": "sri@gmail.com",  "mobile": "9000000002"},
        "naveen": {"password": "3333", "email": "naveen@gmail.com", "mobile": "9000000003"},
        "rishi": {"password": "4444", "email": "rishi@gmail.com", "mobile": "9000000004"},
        "rizwan": {"password": "5555", "email": "rizwan@gmail.com", "mobile": "9000000005"},
    }

    st.session_state.setdefault("client_auth", False)
    st.session_state.setdefault("client_user", "")
    st.session_state.setdefault("client_email", "")
    st.session_state.setdefault("client_mobile", "")

    # --- Login ---
    if not st.session_state["client_auth"]:
        st.subheader("🔐 Client Login")
        with st.form("client_login_form", clear_on_submit=False):
            uname = st.text_input("Username", key="client_uname")
            pwd = st.text_input("Password", type="password", key="client_pwd")
            login_btn = st.form_submit_button("Login")

        if login_btn:
            if uname in users and users[uname]["password"] == pwd:
                st.session_state["client_auth"] = True
                st.session_state["client_user"] = uname
                st.session_state["client_email"] = users[uname].get("email", "")
                st.session_state["client_mobile"] = users[uname].get("mobile", "")
                st.success("Login successful — you can now raise/check queries.")
                safe_rerun()
            else:
                st.error("Invalid username or password.")
        st.stop()

    # --- Logged in area ---
    st.markdown(f"**Logged in as:** `{st.session_state['client_user']}`  —  📧 {st.session_state['client_email']}  |  📱 {st.session_state['client_mobile']}")
    if st.button("Logout", key="client_logout_btn"):
        st.session_state["client_auth"] = False
        st.session_state["client_user"] = ""
        st.session_state["client_email"] = ""
        st.session_state["client_mobile"] = ""
        safe_rerun()

    def clear_new_form_and_rerun():
        for k in ("new_name", "new_email", "new_mobile", "new_query_heading", "new_query_description", "new_checked"):
            if k in st.session_state:
                del st.session_state[k]
        safe_rerun()

    def clear_check_fields():
        # Only clear complaint id and status for the simplified UI
        if "chk_complaint_id" in st.session_state:
            st.session_state["chk_complaint_id"] = ""
        if "chk_status_choice" in st.session_state:
            st.session_state["chk_status_choice"] = "all"

    # two tabs
    tab_new, tab_check = st.tabs(["New Query", "Check Query Status"])

    # New Query tab (unchanged)
    with tab_new:
        st.header("Raise a New Query")
        st.info("Fill the form below and click **Raise Query**. New complaints are created with status = 'open'.")

        new_name = st.text_input("Name", key="new_name")
        new_email = st.text_input("Email", value=st.session_state.get("client_email", ""), key="new_email")
        new_mobile = st.text_input("Mobile number", value=st.session_state.get("client_mobile", ""), key="new_mobile")
        # NEW: heading then description
        new_query_heading = st.text_input("Query Heading", key="new_query_heading")
        new_query_description = st.text_area("Query Description", key="new_query_description", height=150)
        new_checked = st.checkbox("I confirm the information is correct", key="new_checked")

        if st.button("Raise Query", key="raise_query_btn"):
            missing = []
            if not str(new_name).strip(): missing.append("Name")
            if not str(new_email).strip(): missing.append("Email")
            if not str(new_mobile).strip(): missing.append("Mobile")
            if not str(new_query_heading).strip(): missing.append("Query Heading")
            if not str(new_query_description).strip(): missing.append("Query Description")

            if missing:
                st.error("❌ Please fill required fields: " + ", ".join(missing))
            elif not new_checked:
                st.error("❌ Please tick the confirmation checkbox.")
            else:
                try:
                    # decide whether to let DB auto-generate query_id or compute one
                    auto_inc = is_query_id_auto_increment()
                    if auto_inc:
                        insert_sql = """
                            INSERT INTO customer_data (name, email, mobile, query_heading, query_description, status, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """
                        params = (new_name, new_email, new_mobile, new_query_heading, new_query_description, 'open', datetime.now())
                        cur = mydb.cursor()
                        cur.execute(insert_sql, params)
                        mydb.commit()
                        new_id = cur.lastrowid
                        cur.close()
                    else:
                        # compute next query_id and include it in the insert
                        next_id = get_next_query_id()
                        insert_sql = """
                            INSERT INTO customer_data (query_id, name, email, mobile, query_heading, query_description, status, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        params = (next_id, new_name, new_email, new_mobile, new_query_heading, new_query_description, 'open', datetime.now())
                        cur = mydb.cursor()
                        cur.execute(insert_sql, params)
                        mydb.commit()
                        new_id = next_id
                        cur.close()

                    st.success(f"✔ Complaint registered! (ID: {new_id})")
                except Exception as e:
                    st.error(f"Failed to submit complaint: {e}")
                    st.stop()

                # show open complaints for this user
                df = fetch_open_complaints(new_email, new_mobile)
                if not df.empty:
                    st.subheader("Your Open Complaints (including the new one)")
                    display_cols = [c for c in ["query_id","name","email","mobile","query_heading","query_description","status","created_at","closed_at","remarks"] if c in df.columns]
                    st.dataframe(df[display_cols])
                else:
                    st.info("No open complaints found for your contact details (unexpected after insert).")

                if st.button("Done", key=f"done_after_{new_id}"):
                    clear_new_form_and_rerun()

    # Check Query Status tab (SIMPLIFIED)
    with tab_check:
        st.header("Check Query Status")
        st.info("We assure you that all your queries will be resolved soon.")

        # Only show status and complaint id filters
        status_choice = st.selectbox("Filter by status", options=["all", "open", "In Progress", "closed"], index=0, key="chk_status_choice")
        complaint_id_filter = st.text_input("Filter by Complaint ID (optional)", key="chk_complaint_id")

        if st.button("Check Status", key="check_status_btn"):
            # default to logged-in user's email/mobile
            email_val = st.session_state.get("client_email", "") or None
            mobile_val = st.session_state.get("client_mobile", "") or None

            try:
                df_chk = fetch_complaints_lookup(None, email_val, mobile_val, status_choice)
            except Exception as e:
                st.error(f"Lookup failed: {e}")
                st.stop()

            # Complaint ID filter if provided
            if str(complaint_id_filter).strip():
                try:
                    cid = int(str(complaint_id_filter).strip())
                    if "query_id" in df_chk.columns:
                        df_chk = df_chk[df_chk["query_id"] == cid]
                        if df_chk.empty:
                            st.info(f"No complaints found matching Complaint ID {cid} for your account.")
                    else:
                        st.warning("Complaint ID filter not applied: 'query_id' column missing in results.")
                except ValueError:
                    st.error("Complaint ID must be a number. Please enter a valid numeric ID.")

            if df_chk.empty:
                st.info("No complaints found.")
            else:
                st.subheader("Matching Complaints")
                display_cols = [c for c in ["query_id","name","email","mobile","query_heading","query_description","status","created_at","closed_at","remarks"] if c in df_chk.columns]
                st.dataframe(df_chk[display_cols])

                if st.button("Clear Filters", key="clear_lookup_btn"):
                    clear_check_fields()
                    safe_rerun()

# ---------------- Support side ----------------
elif side == 'Support':
    st.title("Support Dashboard")

    # --- static credentials (demo) ---
    SUPPORT_USER = "Support"
    SUPPORT_PASS = "1234"

    st.session_state.setdefault("support_auth", False)
    st.session_state.setdefault("support_user", "")
    st.session_state.setdefault("support_selected_id", None)
    st.session_state.setdefault("support_status_filter", "all")

    # Login form
    if not st.session_state["support_auth"]:
        st.subheader("🔐 Support Login Required")
        with st.form("support_login_form"):
            username = st.text_input("Username", key="support_username")
            password = st.text_input("Password", type="password", key="support_password")
            login_clicked = st.form_submit_button("Login", use_container_width=True)

        if login_clicked:
            if username == SUPPORT_USER and password == SUPPORT_PASS:
                st.session_state["support_auth"] = True
                st.session_state["support_user"] = username
                st.success("Login successful.")
            else:
                st.error("Invalid username or password.")

        if not st.session_state["support_auth"]:
            st.stop()

    st.markdown(f"**Logged in as:** `{st.session_state['support_user']}`")
    if st.button("Logout", key="support_logout_btn"):
        st.session_state["support_auth"] = False
        st.session_state["support_user"] = ""
        st.session_state["support_selected_id"] = None
        safe_rerun()

    # Fetch all complaints for support view (consistent column names)
    try:
        mycursor.execute("""
            SELECT query_id, name, email, mobile, query_heading, query_description, status, created_at, closed_at, remarks
            FROM customer_data
            ORDER BY created_at DESC, query_id DESC
        """)
        remarks_present = True
    except Exception:
        mycursor.execute("""
            SELECT query_id, name, email, mobile, query_heading, query_description, status, created_at, closed_at
            FROM customer_data
            ORDER BY created_at DESC, query_id DESC
        """)
        remarks_present = False

    try:
        rows = mycursor.fetchall()
    except Exception as e:
        st.error(f"Database fetch error: {e}")
        st.stop()

    if not rows:
        st.info("No complaints found.")
    else:
        cols = [d[0] for d in mycursor.description]
        df = pd.DataFrame(rows, columns=cols)

        # Format timestamps if present
        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce").dt.strftime("%d-%m-%Y %H:%M:%S").fillna("")
        if "closed_at" in df.columns:
            df["closed_at"] = pd.to_datetime(df["closed_at"], errors="coerce").dt.strftime("%d-%m-%Y %H:%M:%S").fillna("")
        if "remarks" in df.columns:
            df["remarks"] = df["remarks"].fillna("")

        # --- Status filter options ---
        if "status" in df.columns:
            raw_status = df["status"].dropna().astype(str).unique().tolist()
            status_options = ["all"] + sorted(raw_status)
        else:
            status_options = ["all"]

        status_filter = st.selectbox(
            "Filter by status",
            options=status_options,
            index=status_options.index(st.session_state["support_status_filter"]) if st.session_state["support_status_filter"] in status_options else 0,
            key="support_status_selectbox"
        )
        st.session_state["support_status_filter"] = status_filter

        if status_filter == "all":
            df_view = df.copy()
        else:
            df_view = df[df["status"].astype(str) == str(status_filter)]

        st.subheader("📌 Complaints")
        display_cols = [c for c in ["query_id","name","email","mobile","query_heading","query_description","status","created_at","closed_at","remarks"] if c in df_view.columns]
        st.dataframe(df_view[display_cols])

        if remarks_present:
            st.caption("Remarks column is shown. Click a complaint below to view/edit full remarks.")

        # Manage a complaint
        st.subheader("Manage a complaint")
        id_options = df_view["query_id"].astype(str).tolist()
        if not id_options:
            st.info("No complaints in this filter.")
        else:
            if st.session_state["support_selected_id"] not in id_options:
                st.session_state["support_selected_id"] = id_options[0]

            selected_id = st.selectbox(
                "Select Complaint ID",
                options=id_options,
                index=id_options.index(st.session_state["support_selected_id"]),
                key="support_id_selectbox"
            )
            st.session_state["support_selected_id"] = selected_id

            sel_row = df[df["query_id"] == int(selected_id)].iloc[0]

            # Friendly details
            st.markdown("**Complaint details:**")
            detail_cols = [c for c in ["query_id","name","email","mobile","query_heading","query_description","status","created_at","closed_at"] if c in df.columns]
            for col in detail_cols:
                st.write(f"**{col}:** {sel_row[col]}")

            # Show remarks in expander for reading
            if remarks_present:
                current_remarks = sel_row["remarks"] if pd.notna(sel_row["remarks"]) else ""
                with st.expander("Remarks (visible to client) — click to expand"):
                    if current_remarks.strip():
                        st.write(current_remarks)
                    else:
                        st.info("No remarks for this complaint.")

            # Editable remarks input (pre-filled)
            existing_remarks = sel_row["remarks"] if (remarks_present and "remarks" in sel_row.index and pd.notna(sel_row["remarks"])) else ""
            remarks_input = st.text_area("Edit Remarks (visible to client)", value=existing_remarks, height=120, key=f"remarks_{selected_id}")

            # Current status
            current_status = sel_row["status"] if "status" in sel_row.index else "open"
            st.write(f"Current status: **{current_status}**")

            # Build status options (include any custom status)
            status_radio_options = ["open", "In Progress", "closed"]
            if "status" in sel_row.index and str(sel_row["status"]) not in status_radio_options:
                status_radio_options.insert(0, str(sel_row["status"]))
            try:
                default_idx = status_radio_options.index(str(current_status))
            except ValueError:
                default_idx = 0

            new_status = st.radio(
                "Set new status:",
                options=status_radio_options,
                index=default_idx,
                key=f"support_new_status_radio_{selected_id}"
            )

            # Update button (delete removed per your request)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Update Status", key=f"support_update_btn_{selected_id}"):
                    try:
                        # Build update SQL depending on whether remarks column exists
                        if str(new_status).lower() == "closed":
                            if remarks_present:
                                update_sql = "UPDATE customer_data SET status = %s, closed_at = %s, remarks = %s WHERE query_id = %s"
                                params = (new_status, datetime.now(), remarks_input, int(selected_id))
                            else:
                                update_sql = "UPDATE customer_data SET status = %s, closed_at = %s WHERE query_id = %s"
                                params = (new_status, datetime.now(), int(selected_id))
                        else:
                            if remarks_present:
                                update_sql = "UPDATE customer_data SET status = %s, closed_at = %s, remarks = %s WHERE query_id = %s"
                                params = (new_status, None, remarks_input, int(selected_id))
                            else:
                                update_sql = "UPDATE customer_data SET status = %s, closed_at = %s WHERE query_id = %s"
                                params = (new_status, None, int(selected_id))

                        cur_upd = mydb.cursor()
                        cur_upd.execute(update_sql, params)
                        mydb.commit()
                        cur_upd.close()
                        st.success(f"Status for ID {selected_id} set to '{new_status}' and remarks saved (if available).")
                    except Exception as e:
                        st.error(f"Update failed: {e}")
                    safe_rerun()
            with col2:
                st.write("")  # placeholder to keep layout consistent
