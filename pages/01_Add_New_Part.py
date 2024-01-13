import streamlit as st
import sqlite3
import pandas as pd

"""
# Add New Part
Please enter the information of the part you want to add to your inventory.
Note that the part name must be unique.
"""

part_name = st.text_input('Enter Part name', key='part_name')
lead_time = st.text_input('Enter Lead Time', key='lead_time')
lot_size = st.text_input('Enter Lot Size', key='lot_size')

if st.button('Add'):
    try:
        lead_time = int(lead_time)
        lot_size = int(lot_size) if lot_size else None
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute('SELECT PartName FROM Part WHERE PartName = ?', (part_name,))
        if c.fetchone():
            st.error(f"Part {part_name} already exists.")
        else:
            if lot_size:
                c.execute('INSERT INTO Part (PartName, LeadTime, LotSize) VALUES (?, ?, ?)', (part_name, lead_time, lot_size))
            else:
                c.execute('INSERT INTO Part (PartName, LeadTime) VALUES (?, ?)', (part_name, lead_time))
        conn.commit()
        conn.close()
    except ValueError as e:
        st.error(f"Input error: {e}")
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")

if st.checkbox('Show Part data'):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('SELECT PartName, LeadTime, InitialInventory, LotSize FROM Part')
    data = c.fetchall()
    conn.close()

    # Ensure there's data to display
    if data:
        df = pd.DataFrame(data, columns=['Part Name', 'Lead Time', 'Initial Inventory', 'Lot Size'])
        df.set_index('Part Name', inplace=True)
        st.dataframe(df)
    else:
        st.write("No data available in the Part table.")

if st.button('Delete all Part data'):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('DELETE FROM Part')
    conn.commit()
    conn.close()
    st.success('Part data deleted successfully.')
