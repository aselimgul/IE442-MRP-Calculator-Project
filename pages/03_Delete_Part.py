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

if st.button('Delete'):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('SELECT PartID FROM Part WHERE PartName = ?', (part_name,))
    part_id = c.fetchone()[0]
    c.execute('DELETE FROM MRP WHERE PartID = ?', (part_id,))
    c.execute('DELETE FROM BOM WHERE PartID = ?', (part_id,))
    c.execute('DELETE FROM BOM WHERE ComponentID = ?', (part_id,))
    c.execute('DELETE FROM Part WHERE PartID = ?', (part_id,))
    
    conn.commit()
    conn.close()