import sqlite3
from pathlib import Path
from datetime import date
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).with_name("donors.db")

st.set_page_config(page_title="Blood Donor Record System", page_icon="🩸", layout="wide")

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]


def connect_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS donors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                blood_group TEXT NOT NULL,
                city TEXT NOT NULL,
                contact TEXT,
                last_donation_date TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)



def fetch_donors(search="", group="All"):
    query = "SELECT id, name, blood_group, city, contact, last_donation_date, notes, created_at FROM donors WHERE 1=1"
    params = []
    if search:
        query += " AND (name LIKE ? OR city LIKE ? OR contact LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])
    if group != "All":
        query += " AND blood_group = ?"
        params.append(group)
    query += " ORDER BY name COLLATE NOCASE"
    with connect_db() as conn:
        return pd.read_sql_query(query, conn, params=params)



def add_donor(name, blood_group, city, contact, last_date, notes):
    with connect_db() as conn:
        conn.execute(
            "INSERT INTO donors (name, blood_group, city, contact, last_donation_date, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (name.strip(), blood_group, city.strip(), contact.strip(), last_date or None, notes.strip())
        )



def update_donor(donor_id, name, blood_group, city, contact, last_date, notes):
    with connect_db() as conn:
        conn.execute(
            "UPDATE donors SET name=?, blood_group=?, city=?, contact=?, last_donation_date=?, notes=? WHERE id=?",
            (name.strip(), blood_group, city.strip(), contact.strip(), last_date or None, notes.strip(), donor_id)
        )


def delete_donor(donor_id):
    with connect_db() as conn:
        conn.execute("DELETE FROM donors WHERE id=?", (donor_id,))



init_db()


st.title("🩸 Blood Donor Record System")
st.caption("Student project demonstration using Python, Streamlit and SQLite. Use fictional data only.")


all_data = fetch_donors()
col1, col2, col3 = st.columns(3)
col1.metric("Total Donors", len(all_data))
col2.metric("Blood Groups", all_data["blood_group"].nunique() if not all_data.empty else 0)
col3.metric("Cities", all_data["city"].nunique() if not all_data.empty else 0)

st.divider()
page = st.sidebar.radio("Navigation", ["Dashboard & Search", "Add Donor", "Manage Donors", "Export"])

if page == "Dashboard & Search":
    st.subheader("Donor Directory")
    search_text = st.text_input("Search by name, city or contact")
    selected_group = st.selectbox("Filter by blood group", ["All"] + BLOOD_GROUPS)
    donors = fetch_donors(search_text, selected_group)
    st.dataframe(donors.drop(columns=["created_at"], errors="ignore"), use_container_width=True, hide_index=True)
    if donors.empty:
        st.info("No records found. Add a donor from the sidebar.")

elif page == "Add Donor":
    st.subheader("Register a Donor")
    with st.form("add_donor_form", clear_on_submit=True):
        name = st.text_input("Full name *")
        blood_group = st.selectbox("Blood group *", BLOOD_GROUPS)
        city = st.text_input("City *")
        contact = st.text_input("Contact (fictional for demo)")
        last_date = st.date_input("Last donation date (optional)", value=None, min_value=date(1950, 1, 1), max_value=date.today())
        notes = st.text_area("Notes (optional)")
        submitted = st.form_submit_button("Save Donor")
        if submitted:
            if not name.strip() or not city.strip():
                st.error("Please enter the donor's name and city.")
            else:
                add_donor(name, blood_group, city, contact, last_date.isoformat() if last_date else "", notes)
                st.success("Donor record added successfully!")
                st.rerun()

elif page == "Manage Donors":
    st.subheader("Update or Delete a Record")
    donors = fetch_donors()
    if donors.empty:
        st.info("No donors to manage yet.")
    else:
        donor_choices = {f"{row['name']} — {row['blood_group']} — {row['city']} (ID {row['id']})": int(row['id']) for _, row in donors.iterrows()}
        selected_label = st.selectbox("Choose donor", list(donor_choices.keys()))
        donor_id = donor_choices[selected_label]
        record = donors[donors.id == donor_id].iloc[0]
        with st.form("edit_donor_form"):
            name = st.text_input("Full name", value=record["name"])
            blood_group = st.selectbox("Blood group", BLOOD_GROUPS, index=BLOOD_GROUPS.index(record["blood_group"]))
            city = st.text_input("City", value=record["city"])
            contact = st.text_input("Contact (fictional for demo)", value=record["contact"] or "")
            last_raw = record["last_donation_date"] or ""
            default_date = date.fromisoformat(last_raw) if last_raw else None
            last_date = st.date_input("Last donation date", value=default_date, min_value=date(1950, 1, 1), max_value=date.today())
            notes = st.text_area("Notes", value=record["notes"] or "")
            save = st.form_submit_button("Update donor")
            if save:
                if not name.strip() or not city.strip():
                    st.error("Name and city are required.")
                else:
                    update_donor(donor_id, name, blood_group, city, contact, last_date.isoformat() if last_date else "", notes)
                    st.success("Donor updated.")
                    st.rerun()
        if st.button("Delete selected donor", type="secondary"):
            st.session_state["confirm_delete"] = donor_id
        if st.session_state.get("confirm_delete") == donor_id:
            st.warning("Confirm deleting this record?")
            confirm_col, cancel_col = st.columns(2)
            if confirm_col.button("Confirm delete", type="primary"):
                delete_donor(donor_id)
                st.session_state.pop("confirm_delete", None)
                st.success("Record deleted.")
                st.rerun()
            if cancel_col.button("Cancel"):
                st.session_state.pop("confirm_delete", None)
                st.rerun()

elif page == "Export":
    st.subheader("Export Donor Records")
    donors = fetch_donors()
    st.write(f"Records available: **{len(donors)}**")
    csv_bytes = donors.to_csv(index=False).encode("utf-8")
    st.download_button("Download donor records as CSV", data=csv_bytes, file_name="donor_records_demo.csv", mime="text/csv", disabled=donors.empty)
    st.caption("Only export fictional/demo data. Do not publish personal donor information.")

st.sidebar.caption("Demo only — do not store or publish real donor contact details in this public app.")
