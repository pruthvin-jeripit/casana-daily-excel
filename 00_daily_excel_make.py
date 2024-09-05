import pandas as pd
import re
import streamlit as st

# Function to clean phone numbers
def clean_phone_number(phone_number):
    if pd.isnull(phone_number):
        return phone_number  # If the phone number is NaN, return it as is
    phone_number = str(phone_number)  # Ensure the phone number is a string
    
    # Remove apostrophe and country code if present (e.g., "'+1")
    phone_number = re.sub(r"^'\+1\s*", '', phone_number)
    
    # Remove unwanted characters (anything that is not a digit)
    cleaned_number = re.sub(r'[^\d]', '', phone_number)
    
    # Format the number
    if len(cleaned_number) == 10:
        return f'({cleaned_number[:3]}) {cleaned_number[3:6]}-{cleaned_number[6:]}'
    else:
        return phone_number  # Return the original if it doesn't match the expected length

# Load the CSV files
uploaded_booking_file = st.file_uploader("Upload Booking CSV")
uploaded_master_file = st.file_uploader("Upload Master CSV")

if uploaded_booking_file and uploaded_master_file:
    # Extract date from booking file name
    booking_filename = uploaded_booking_file.name
    date_part = booking_filename.split('_')[1].split('-')[0]

    # Load the CSV files into DataFrames
    booking_df = pd.read_csv(uploaded_booking_file)
    master_df = pd.read_csv(uploaded_master_file)

    # Check the column names in booking_df to ensure we are using the correct one
    st.write("Booking Data Columns:", booking_df.columns)

    # Use the correct column name for extracting time, adjust the name if necessary
    correct_column_name = [col for col in booking_df.columns if 'time' in col.lower()][0]

    # Process booking_df
    booking_df = booking_df[booking_df['Status'] == 'Scheduled']
    booking_df['phone_number'] = booking_df['phone_number'].apply(clean_phone_number)
    booking_df['appointment_time'] = booking_df[correct_column_name].str.extract(r'(\d{1,2}:\d{2} [AP]M)')
    booking_df = booking_df.drop(columns=['Status', correct_column_name])

    # Process master_df
    master_df['record_id'] = master_df['record_id'].astype(str) + '-B'
    master_df = master_df[['record_id', 'phy_skin', 'phy_sternal', 'phy_waist_circ', 'phy_arm']]

    # Merge DataFrames on 'record_id'
    daily_df = pd.merge(booking_df, master_df, on='record_id', how='left')

    # Reorder columns in daily_df
    desired_order = [
        'appointment_time', 'record_id', 'first_name', 'last_name', 
        'Customer email', 'phone_number', 'phy_skin', 'phy_sternal', 
        'phy_waist_circ', 'phy_arm'
    ]
    daily_df = daily_df[desired_order]

    # Save the result to an Excel file
    output_filename = f'{date_part}.xlsx'
    daily_df.to_excel(output_filename, index=False)

    # Show the final DataFrame in Streamlit
    st.write("Final Merged Data:")
    st.dataframe(daily_df)

    # Check if original booking_df and daily_df have the same number of rows
    booking_rows = booking_df.shape[0]
    daily_rows = daily_df.shape[0]

    # Display the result in Streamlit
    if booking_rows == daily_rows:
        st.write(f"✅ The original booking data has {booking_rows} rows, and the final merged data has {daily_rows} rows. The row count matches.")
    else:
        st.write(f"⚠️ The original booking data has {booking_rows} rows, but the final merged data has {daily_rows} rows. The row count does not match.")

        # Find the missing record_ids in daily_df
        missing_record_ids = booking_df[~booking_df['record_id'].isin(daily_df['record_id'])]

        if not missing_record_ids.empty:
            # Perform the same cleaning on the missing records
            missing_record_ids['appointment_time'] = missing_record_ids[correct_column_name].str.extract(r'(\d{1,2}:\d{2} [AP]M)')
            missing_record_ids['phone_number'] = missing_record_ids['phone_number'].apply(clean_phone_number)

            # Create a DataFrame with null values for columns that come from master_df
            missing_record_ids = missing_record_ids.assign(
                phy_skin=pd.NA,
                phy_sternal=pd.NA,
                phy_waist_circ=pd.NA,
                phy_arm=pd.NA
            )

            # Drop unnecessary columns
            missing_record_ids = missing_record_ids.drop(columns=['Status', correct_column_name])

            # Reorder columns in missing_record_ids to match daily_df structure
            missing_record_ids = missing_record_ids[desired_order]

            # Append missing records to daily_df
            daily_df = pd.concat([daily_df, missing_record_ids], ignore_index=True)

            # Display the updated DataFrame in Streamlit
            st.write(f"Added {missing_record_ids.shape[0]} missing records to the final data.")
        else:
            st.write("No missing records found in booking data.")

    # Option to download the result as an Excel file
    with open(output_filename, 'rb') as f:
        st.download_button(label="Download Merged Excel File", data=f, file_name=output_filename, mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    # Consent file upload
    uploaded_consent_file = st.file_uploader("Upload Consent Form CSV")

    if uploaded_consent_file:
        # Load the consent CSV file into a DataFrame
        consent_df = pd.read_csv(uploaded_consent_file)

        # Filter the required columns
        consent_df_filtered = consent_df[['record_id', 'icf_first_name', 'icf_last_name']]
        daily_df_filtered = daily_df[['record_id', 'first_name', 'last_name']]

        # Add '-B' to the record_id in consent_df
        consent_df_filtered['record_id'] = consent_df_filtered['record_id'].astype(str) + '-B'

        # Perform an inner join on record_id
        merged_df = pd.merge(consent_df_filtered, daily_df_filtered, on='record_id', how='inner')

        # Identify rows where first_name or last_name do not match
        unmatched_names_df = merged_df[
            (merged_df['icf_first_name'] != merged_df['first_name']) |
            (merged_df['icf_last_name'] != merged_df['last_name'])
        ]

        # Check if there are any unmatched names
        if not unmatched_names_df.empty:
            st.write("There are unmatched names:")
            st.dataframe(unmatched_names_df)

            # Save the unmatched names to an Excel file
            unmatched_output_filename = f'Unmatched_{date_part}.xlsx'
            unmatched_names_df.to_excel(unmatched_output_filename, index=False)

            # Provide download option for the unmatched names
            with open(unmatched_output_filename, 'rb') as f:
                st.download_button(label="Download Unmatched Names Excel File", data=f, file_name=unmatched_output_filename, mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        else:
            st.write("All names are matched.")
