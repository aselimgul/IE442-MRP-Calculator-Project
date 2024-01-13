import streamlit as st
import sqlite3
import pandas as pd

def create_table():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS Period (PeriodID INTEGER PRIMARY KEY)')
    c.execute('CREATE TABLE IF NOT EXISTS Part (PartID INTEGER PRIMARY KEY AUTOINCREMENT, PartName VARCHAR(20), LeadTime INTEGER, InitialInventory INTEGER, LotSize INTEGER, BOMLevel INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS BOM (PartID INTEGER, ComponentID INTEGER, Multiplier INTEGER, Level INTEGER, PRIMARY KEY (PartID, ComponentID))')
    c.execute('CREATE TABLE IF NOT EXISTS MRP (PartID INTEGER, PeriodID INTEGER, GrossRequirements INTEGER, ScheduledReceipts INTEGER, EndingInventory INTEGER, NetRequirements INTEGER, PlannedOrderRelease INTEGER, PlannedOrderReceipt INTEGER, PRIMARY KEY (PeriodID, PartID))')
    conn.commit()
    conn.close()

create_table()

"""
# WELCOME TO MRP CALCULATOR
This is a simple MRP calculator developed for IE442 course project at Bogazici University.

## How to use this app?
1. Go to the **Add New Part** page and add the parts you need to your inventory.
2. Go to the **Add 1st Level Components to BOM** page and add the 1st level components of your parts.
3. Go to **MRP Calculator** page and calculate the MRP for your product.

To delete a part, go to the **Delete Part** page and select the part you want to delete.
To delete a part-component relation, go to the **Delete Part-Component Relation** page and select the part and component you want to delete.
"""

