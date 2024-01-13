import streamlit as st
import sqlite3
import pandas as pd

part_name = st.text_input('Enter Part name', key='part_name')
component_name = st.text_input('Enter 1st level component name', key='component_name')
multiplier = st.text_input('Enter multiplier', key='multiplier')

if st.button('Add'):
    try:
        multiplier = int(multiplier)
        conn = sqlite3.connect('data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT PartID FROM Part WHERE PartName = (?)', (part_name,))
        part_id = cursor.fetchone()[0]
        cursor.execute('SELECT PartID FROM Part WHERE PartName = (?)', (component_name,))
        component_id = cursor.fetchone()[0]
        cursor.execute('INSERT INTO BOM (PartID, ComponentID, Multiplier, Level) VALUES (?, ?, ?, 1)', (part_id, component_id, multiplier))
        conn.commit()
        conn.close()
    except ValueError as e:
        st.error(f"Input error: {e}")
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")

if st.checkbox('Show raw data'):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('SELECT * FROM BOM')
    data = c.fetchall()
    conn.close()

    # Ensure there's data to display
    if data:
        df = pd.DataFrame(data, columns=['Part ID', 'Component ID', 'Multiplier', 'Level'])  # Replace with actual column names
        st.dataframe(df)
    else:
        st.write("No data available in the BOM table.")

if st.button('Delete all BOM data'):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('DELETE FROM BOM')
    conn.commit()
    conn.close()
    st.success('BOM data deleted successfully.')