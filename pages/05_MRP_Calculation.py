import streamlit as st
import sqlite3
import pandas as pd

# Function to insert Period information into the Period table
def select_number_of_periods(number):
    for i in range(number):
        cursor.execute("INSERT INTO Period VALUES (?)", (i+1,))
    connection.commit()

# Insert MRP information into the MRP table based on main Product
def get_mrp_info(part_name):

    # Insert final Product to MRP table
    cursor.execute("SELECT PeriodID FROM Period ORDER BY PeriodID DESC LIMIT 1;")
    max_period = cursor.fetchone()[0]
    cursor.execute("SELECT PartID FROM Part WHERE PartName = ?", (part_name))
    part_id = cursor.fetchone()[0]
    for i in range(max_period):
        cursor.execute("INSERT INTO MRP (PartID, PeriodID) VALUES (?, ?)", (part_id, i+1))
    connection.commit()

    # Insert components to MRP table
    cursor.execute("""
        WITH ComponentHierarchy AS (
        SELECT 
            BOM.PartID, 
            BOM.ComponentID, 
            BOM.Multiplier, 
            BOM.Level
        FROM 
            BOM
        WHERE 
            PartID = ?

        UNION ALL

        SELECT 
            ch.PartID,
            b.ComponentID, 
            b.Multiplier * ch.Multiplier AS Multiplier, 
            ch.Level + 1
        FROM 
            BOM b
        INNER JOIN 
            ComponentHierarchy ch ON b.PartID = ch.ComponentID
        )

        INSERT INTO MRP (PartID, PeriodID)
        SELECT DISTINCT(c.ComponentID), p.PeriodID 
        FROM ComponentHierarchy c, Period p 
        WHERE c.PartID = ?;  

    """, (part_id, part_id))
    connection.commit()


def calculate_net_requirements(part_name):
    cursor = connection.cursor()
    cursor.execute("SELECT PartID FROM Part WHERE PartName = ?", (part_name,))
    part_id = cursor.fetchone()[0]
    cursor.execute("SELECT ComponentID FROM BOM WHERE PartID = ?", (part_id,))
    components = cursor.fetchall()
    components = [i[0] for i in components]
    cursor.execute("UPDATE MRP SET NetRequirements = GrossRequirements - COALESCE(ScheduledReceipts, 0) WHERE PartID = ?", (part_id,))
    connection.commit()

    while True:
        # Find the first period with negative net requirements
        cursor.execute("""
            SELECT PeriodID, NetRequirements
            FROM MRP
            WHERE PartID = ? AND NetRequirements < 0
            ORDER BY PeriodID ASC LIMIT 1;
            """, (part_id,))
        negative_period = cursor.fetchone()

        if not negative_period:
            # Exit the loop if there are no negative net requirements
            break

        negative_period_id, negative_net_req = negative_period

        # Find the next period with positive net requirements to offset the negative amount
        cursor.execute("""
            SELECT PeriodID
            FROM MRP
            WHERE PartID = ? AND PeriodID > ? AND NetRequirements > 0
            ORDER BY PeriodID ASC LIMIT 1;
            """, (part_id, negative_period_id))
        positive_period_id = cursor.fetchone()

        if not positive_period_id:
            # Exit the loop if there are no positive net requirements to offset the negative ones
            break

        positive_period_id = positive_period_id[0]

        # Update the net requirements of both periods
        cursor.execute("""
            UPDATE MRP
            SET NetRequirements = 0
            WHERE PartID = ? AND PeriodID = ?;
            """, (part_id, negative_period_id))

        cursor.execute("""
            UPDATE MRP
            SET NetRequirements = NetRequirements + ?
            WHERE PartID = ? AND PeriodID = ?;
            """, (negative_net_req, part_id, positive_period_id))

        connection.commit()

    # while True:
    #     count = 0
    #     if count > 500:
    #         break
    #     cursor.execute("""
    #         SELECT PeriodID, NetRequirements
    #         FROM MRP
    #         WHERE PartID = ? AND NetRequirements < 0
    #         ORDER BY PeriodID ASC LIMIT 1;
    #         """, (part_id,))
    #     result = cursor.fetchone()
    #     if result:
    #         count += 1
    #         cursor.execute("""
    #             SELECT MIN(PeriodID) as NearestPositivePeriodID
    #             FROM MRP
    #             WHERE PartID = ? AND PeriodID > ? AND NetRequirements > 0;
    #             """, (part_id, result[0]))
    #         nearest_positive_period_id = cursor.fetchone()
    #         if nearest_positive_period_id:
    #             cursor.execute("""
    #                     UPDATE MRP
    #                     SET NetRequirements = NetRequirements + (SELECT NetRequirements FROM MRP WHERE PartID = ? AND PeriodID = ?)
    #                     WHERE PartID = ? AND PeriodID = ?;
    #                     """, (part_id, result[0], part_id, nearest_positive_period_id[0]))
    #             cursor.execute("""
    #                     UPDATE MRP
    #                     SET NetRequirements = 0
    #                     WHERE PartID = ? AND PeriodID = ?;
    #                     """, (part_id, result[0]))
    #             connection.commit()
    #         else:
    #             break
    #     else:
    #         break


    if len(components) > 0:
        cursor.execute("""

            WITH NetRequirementsA AS (
                SELECT 
                    PeriodID, 
                    NetRequirements
                FROM 
                    MRP
                WHERE 
                    PartID = ?
            ),
            ComponentInfo AS (
                SELECT 
                    b.ComponentID, 
                    b.Multiplier, 
                    p.LeadTime
                FROM 
                    BOM b
                INNER JOIN 
                    Part p ON b.ComponentID = p.PartID
                WHERE 
                    b.PartID = ?
            ),
            GrossRequirementsComponents AS (
                SELECT 
                    c.ComponentID, 
                    n.PeriodID - c.LeadTime AS PeriodID, 
                    n.NetRequirements * c.Multiplier AS GrossRequirements
                FROM 
                    NetRequirementsA n
                CROSS JOIN 
                    ComponentInfo c
            ),
            MRPComponents AS (
            SELECT * FROM MRP LEFT JOIN GrossRequirementsComponents g ON MRP.PartID = g.ComponentID AND MRP.PeriodID = g.PeriodID
            )

            UPDATE MRP
            SET 
                GrossRequirements = COALESCE(GrossRequirements, 0) + (
                    SELECT COALESCE(SUM(g.GrossRequirements), 0)
                    FROM GrossRequirementsComponents g 
                    WHERE g.ComponentID = MRP.PartID AND g.PeriodID = MRP.PeriodID
                )
            WHERE 
                PartID IN (SELECT ComponentID FROM BOM WHERE PartID = ?);

                    """, (part_id, part_id, part_id))
        for element in components:
            cursor.execute("SELECT PartName FROM Part WHERE PartID = ?", (element,))
            name = cursor.fetchone()[0]
            calculate_net_requirements(name)
        

def calculate_first_period_inventory():
    cursor.execute("SELECT DISTINCT(PartID) FROM MRP")
    parts = cursor.fetchall()
    parts = [i[0] for i in parts]
    for element in parts:
        cursor.execute("""
            UPDATE MRP
            SET EndingInventory = (SELECT InitialInventory FROM Part WHERE PartID = ?) - NetRequirements
            WHERE MRP.PeriodID = 1 AND MRP.PartID = ?;
            """, (element, element))
    connection.commit()


def make_first_inv_calculations():
    cursor.execute("SELECT DISTINCT(PartID) FROM MRP")
    parts = cursor.fetchall()
    parts = [i[0] for i in parts]
    for element in parts:

        cursor.execute("""
                WITH RecursiveCTE AS (
                SELECT 
                    PartID, 
                    PeriodID, 
                    EndingInventory,
                    NetRequirements,
                    1 AS RowNum 
                FROM 
                    MRP
                WHERE 
                    PeriodID = 1 AND PartID = ?

                UNION ALL

                SELECT 
                    MRP.PartID, 
                    MRP.PeriodID,
                    RecursiveCTE.EndingInventory + IFNULL(MRP.ScheduledReceipts, 0) - COALESCE(MRP.GrossRequirements, 0),
                    MRP.NetRequirements,
                    RecursiveCTE.RowNum + 1
                FROM 
                    MRP
                INNER JOIN 
                    RecursiveCTE 
                    ON MRP.PartID = RecursiveCTE.PartID AND MRP.PeriodID = RecursiveCTE.PeriodID + 1
                WHERE 
                    MRP.PartID = ?
            )
            UPDATE MRP
            SET 
                EndingInventory = (
                    SELECT EndingInventory
                    FROM RecursiveCTE
                    WHERE 
                        RecursiveCTE.PartID = MRP.PartID AND 
                        RecursiveCTE.PeriodID = MRP.PeriodID
                )
            WHERE 
                PartID = ?;


            """, (element, element, element))
        connection.commit()


def make_inv_calculations(part_name):
    cursor.execute("SELECT PartID FROM Part WHERE PartName = ?", (part_name,))
    part_id = cursor.fetchone()[0]
    cursor.execute("""  
                WITH RECURSIVE RecursiveCTE AS (
                    SELECT 
                        PartID, 
                        PeriodID, 
                        EndingInventory, 
                        NetRequirements,
                        1 AS RowNum 
                    FROM 
                        MRP
                    WHERE 
                        PeriodID = 1 AND PartID = ?

                    UNION ALL

                    SELECT 
                        MRP.PartID, 
                        MRP.PeriodID,
                        RecursiveCTE.EndingInventory + IFNULL(MRP.ScheduledReceipts, 0) + IFNULL(MRP.PlannedOrderReceipt, 0) - MRP.GrossRequirements,
                        MRP.NetRequirements,
                        RecursiveCTE.RowNum + 1
                    FROM 
                        MRP
                    INNER JOIN 
                        RecursiveCTE 
                        ON MRP.PartID = RecursiveCTE.PartID AND MRP.PeriodID = RecursiveCTE.PeriodID + 1
                    WHERE 
                        MRP.PartID = ?
                )
                       
                UPDATE MRP
                SET 
                    EndingInventory = (
                        SELECT EndingInventory
                        FROM RecursiveCTE
                        WHERE 
                            RecursiveCTE.PartID = MRP.PartID AND 
                            RecursiveCTE.PeriodID = MRP.PeriodID
                    )
                WHERE 
                    PartID = ?;
                    
        """, (part_id, part_id, part_id))
    connection.commit()


def calculate_planned_order_receipt():
    cursor.execute("""

        WITH LotSize AS (
        SELECT Part.LotSize
        FROM Part
        INNER JOIN MRP ON Part.PartID = MRP.PartID
        WHERE MRP.EndingInventory < 0
        ORDER BY Part.PartID
        LIMIT 1
    )
    UPDATE MRP
    SET PlannedOrderReceipt = COALESCE(
        CAST(
            (-EndingInventory / (SELECT LotSize FROM LotSize)) + 
            (CASE WHEN -EndingInventory % (SELECT LotSize FROM LotSize) > 0 THEN 1 ELSE 0 END)
        AS INTEGER) * (SELECT LotSize FROM LotSize),
        -EndingInventory
    )
    WHERE PeriodID = (
        SELECT PeriodID
        FROM MRP
        WHERE EndingInventory < 0 AND PartID = (SELECT MIN(PartID) FROM MRP WHERE EndingInventory < 0)
        ORDER BY PeriodID
        LIMIT 1
    ) 
    AND PartID = (SELECT MIN(PartID) FROM MRP WHERE EndingInventory < 0);

        """)
    connection.commit()

def calculate_planned_order_release():
    cursor.execute("""
        
        UPDATE MRP SET PlannedOrderRelease = (
            SELECT por.PlannedOrderReceipt
            FROM MRP por
            INNER JOIN Part p ON MRP.PartID = p.PartID
            WHERE por.PartID = MRP.PartID AND por.PeriodID = MRP.PeriodID + p.LeadTime
        )
        WHERE EXISTS (
            SELECT 1
            FROM MRP por
            INNER JOIN Part p ON MRP.PartID = p.PartID
            WHERE por.PartID = MRP.PartID AND por.PeriodID = MRP.PeriodID + p.LeadTime
        );


        """)
    connection.commit()

def make_mrp_calculations():
    cursor.execute("SELECT DISTINCT(PartID) FROM MRP")
    parts = cursor.fetchall()
    parts = [i[0] for i in parts]
    count = 0
    part = parts[count]
    while True:
        cursor.execute("SELECT EndingInventory FROM MRP WHERE PartID = ? AND PeriodID > 0 AND EndingInventory < 0", (part,))
        negative_inventory = cursor.fetchall()
        if negative_inventory:
            calculate_planned_order_receipt()
            cursor.execute("SELECT PartName FROM Part WHERE PartID = ?", (part,))
            part_name = cursor.fetchone()[0]
            make_inv_calculations(part_name)
            continue
        elif part == parts[-1]:
            break
        else:
            count += 1
            part = parts[count]
            continue
    
    calculate_planned_order_release()

    connection.commit()



def check_feasibility(part_name):
    cursor.execute("SELECT PartID FROM Part WHERE PartName = ?", (part_name,))
    part_id = cursor.fetchone()[0]
    cursor.execute("""
        WITH RECURSIVE ComponentLeadTime AS (
        -- Start with the final product itself
        SELECT 
            p.PartID, 
            p.PartID as ComponentID, -- The product is its own 'component' at the start
            p.LeadTime AS ComponentLeadTime,
            0 AS Level -- Level 0 for the product itself
        FROM 
            Part p
        WHERE 
            p.PartID = ? -- Replace with your actual product name
        
        UNION ALL
        
        -- Now add the lead times of all components recursively
        SELECT 
            clt.PartID,
            b.ComponentID, 
            p.LeadTime + clt.ComponentLeadTime AS ComponentLeadTime, 
            clt.Level + 1
        FROM 
            BOM b
        INNER JOIN 
            ComponentLeadTime clt ON b.PartID = clt.ComponentID
        INNER JOIN 
            Part p ON b.ComponentID = p.PartID
        )
        SELECT MAX(ComponentLeadTime) FROM ComponentLeadTime;

        """, (part_id,))
    max_lead_time = cursor.fetchall()[0][0]
    cursor.execute("SELECT PeriodID FROM MRP WHERE PartID = ? AND EndingInventory < 0 ORDER BY PeriodID ASC LIMIT 1", (part_id,))

    result = cursor.fetchone()
    if result:
        first_negative_period = result[0]
    else:
        first_negative_period = 10000000 
    if first_negative_period <= max_lead_time:
        return False
    return True


# Initialize Streamlit session state variables
if 'data_loaded' not in st.session_state:
    st.session_state['data_loaded'] = False

# Connect to database and fetch parts list
connection = sqlite3.connect('data.db')
cursor = connection.cursor()
response = cursor.execute("SELECT PartName FROM Part")
parts = response.fetchall()
part_list = [part[0] for part in parts]

part_to_produce = st.selectbox('Select the part you want to produce', part_list, key='part_to_produce')
periods = st.number_input('Enter the number of periods', key='periods', min_value=1, value=1)


# Button to load data
if st.button('Load Data'):
    # Clear existing data in tables
    cursor.execute("DELETE FROM MRP")
    cursor.execute("DELETE FROM Period")
    connection.commit()

    # Load new data
    select_number_of_periods(periods)
    get_mrp_info(part_to_produce)
    st.session_state['data_loaded'] = True

# Display DataEditors if data is loaded
if st.session_state['data_loaded']:
    cursor.execute('SELECT PartID FROM Part WHERE PartName = ?', (part_to_produce))
    part_to_produce_id = cursor.fetchone()[0]

    cursor.execute('''
    SELECT DISTINCT Part.PartName, Part.InitialInventory
    FROM Part
    INNER JOIN MRP ON Part.PartID = MRP.PartID ORDER BY PartName; 
        ''')
    initial_inventories = cursor.fetchall()

    cursor.execute('''SELECT PartName, PeriodID, GrossRequirements, ScheduledReceipts 
                 FROM MRP INNER JOIN Part ON MRP.PartID = Part.PartID 
                 WHERE Part.PartID = ? 
                 ORDER BY PartName''', (part_to_produce_id,))
    data_product = cursor.fetchall()

    cursor.execute('''SELECT PartName, PeriodID, ScheduledReceipts 
                 FROM MRP INNER JOIN Part ON MRP.PartID = Part.PartID 
                 WHERE Part.PartID <> ? 
                 ORDER BY PartName''', (part_to_produce_id,))
    data_components = cursor.fetchall()

    if initial_inventories:
        df = pd.DataFrame(initial_inventories, columns=['PartName', 'InitialInventory'])
        df["InitialInventory"] = 0
        st.write("Please enter the initial inventories of the parts.")
        initial_inventories_data = st.data_editor(df, column_config={"InitialInventory":st.column_config.NumberColumn(default=0, step=1)}, disabled=("PartName",))
        if data_product:
            df = pd.DataFrame(data_product, columns=['PartName', 'PeriodID', 'GrossRequirements', 'ScheduledReceipts'])
            df["GrossRequirements"] = 0
            df["ScheduledReceipts"] = 0
            st.write("Please enter the gross requirements and scheduled receipts of the product.")
            product_data = st.data_editor(df, column_config={"GrossRequirements":st.column_config.NumberColumn(default=0, step=1), "ScheduledReceipts":st.column_config.NumberColumn(default=0, step=1)}, disabled=("PartName", "PeriodID"))

            if data_components:
                df = pd.DataFrame(data_components, columns=['PartName', 'PeriodID', 'ScheduledReceipts'])
                df["ScheduledReceipts"] = 0
                st.write("Please enter the scheduled receipts of the components.")
                components_data = st.data_editor(df, column_config={"ScheduledReceipts":st.column_config.NumberColumn(default=0, step=1)}, disabled=("PartName", "PeriodID"))
        
    else:
        st.write("No data available in the MRP table.")
    
    if st.button('Calculate'):
        # Update initial inventories
        for index, row in initial_inventories_data.iterrows():
            part_id = cursor.execute("SELECT PartID FROM Part WHERE PartName = ?", (row['PartName'],)).fetchone()[0]
            cursor.execute("UPDATE Part SET InitialInventory = ? WHERE PartID = ?", (row['InitialInventory'], part_id))

        # Update MRP table
        for index, row in product_data.iterrows():
            cursor.execute("UPDATE MRP SET GrossRequirements = ?, ScheduledReceipts = ? WHERE PartID = ? AND PeriodID = ?", (row['GrossRequirements'], row['ScheduledReceipts'], part_to_produce_id, row['PeriodID']))
        
        if data_components:
            for index, row in components_data.iterrows():
                part_id = cursor.execute("SELECT PartID FROM Part WHERE PartName = ?", (row['PartName'],)).fetchone()[0]
                cursor.execute("UPDATE MRP SET ScheduledReceipts = ? WHERE PartID = ? AND PeriodID = ?", (row['ScheduledReceipts'], part_id, row['PeriodID']))
            connection.commit()
        

        # Calculate Net Requirements
        calculate_net_requirements(part_to_produce)
        connection.commit()



        calculate_first_period_inventory()
        connection.commit()
        make_first_inv_calculations()
        connection.commit()
        is_feasible = check_feasibility(part_to_produce)
        if is_feasible:
            make_mrp_calculations()

            connection.commit()
            connection.commit()
            cursor.execute('SELECT DISTINCT(PartName) FROM Part WHERE PartID IN (SELECT DISTINCT(PartID) FROM MRP)')
            parts = cursor.fetchall()
            parts_list = [i[0] for i in parts]
            for part in parts_list:
                make_inv_calculations(part)
            connection.commit()

            st.success("MRP calculation is completed successfully. Please remember that, if you want to change the inputs, you need to load the data again.")
            # Display MRP table
            cursor.execute("""SELECT Part.PartName, MRP.PeriodID, MRP.GrossRequirements, MRP.ScheduledReceipts, MRP.EndingInventory, 
                    MRP.NetRequirements, MRP.PlannedOrderRelease, MRP.PlannedOrderReceipt
                    FROM MRP 
                    JOIN Part ON MRP.PartID = Part.PartID 
                    ORDER BY MRP.PartID""")
            data = cursor.fetchall()
            connection.close()
            df = pd.DataFrame(data, columns=['PartName', 'PeriodID', 'GrossRequirements', 'ScheduledReceipts', 'EndingInventory', 'NetRequirements', 'PlannedOrderRelease', 'PlannedOrderReceipt'])
            df.set_index("PartName", inplace=True)
            st.dataframe(df)
        else:
            st.error("There is no feasible solution for the given inputs. Please try with different inputs.")

