import streamlit as st
import sqlite3
import pandas as pd

connection = sqlite3.connect('data.db')
cursor = connection.cursor()
response = cursor.execute("SELECT PartName FROM Part")
parts = response.fetchall()
part_list = [part[0] for part in parts]
connection.close()

part_name = st.selectbox('Select Part', part_list, key='part_name')
component_name = st.selectbox('Select Component', part_list, key='component_name')

if st.button('Delete'):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('SELECT PartID FROM Part WHERE PartName = ?', (part_name,))
    part_id = c.fetchone()[0]
    c.execute('SELECT PartID FROM Part WHERE PartName = ?', (component_name,))
    component_id = c.fetchone()[0]

    c.execute('SELECT * FROM BOM WHERE PartID = ? AND ComponentID = ?', (part_id, component_id))
    data = c.fetchall()
    if not data:
        st.error('Part-Component relation does not exist.')
    else:
        c.execute('DELETE FROM BOM WHERE PartID = (?) AND ComponentID = (?)', (part_id, component_id))
        conn.commit()
        st.success('Part-Component relation deleted successfully.')
    conn.close()
   