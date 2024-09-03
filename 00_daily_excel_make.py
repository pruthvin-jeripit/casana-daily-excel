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

    # Process booking_df
    booking_df = booking_df[booking_df['Status'] == 'Scheduled']
    booking_df['phone_number'] = booking_df['phone_number'].apply(clean_phone_number)
    booking_df['appointment_time'] = booking_df['Meeting date and time in Owner\'s time zone'].str.extract(r'(\d{1,2}:\d{2} [AP]M)')
    booking_df = booking_df.drop(columns=['Status', 'Meeting date and time in Owner\'s time zone'])

    # Process master_df
    master_df['record_id'] = master_df['record_id'].astype(str) + '-B'
    master_df = master_df[['record_id', 'phy_skin', 'phy_sternal', 'phy_waist_circ', 'phy_arm']]

    # Merge DataFrames on 'record_id'
    daily_df = pd.merge(booking_df, master_df, on='record_id')

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
