import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import matplotlib.pyplot as plt

# Title of the application
st.title("Advanced Analysis: B2B Courier Charges Accuracy")

# Sidebar for file uploads
st.sidebar.header("Upload Your Files")
order_report_file = st.sidebar.file_uploader("Upload Order Report CSV", type="csv")
sku_master_file = st.sidebar.file_uploader("Upload SKU Master CSV", type="csv")
pincode_mapping_file = st.sidebar.file_uploader("Upload Pincode Mapping CSV", type="csv")
courier_invoice_file = st.sidebar.file_uploader("Upload Courier Invoice CSV", type="csv")
courier_rates_file = st.sidebar.file_uploader("Upload Courier Rates CSV", type="csv")

if order_report_file and sku_master_file and pincode_mapping_file and courier_invoice_file and courier_rates_file:
    # Load datasets
    order_report = pd.read_csv(order_report_file)
    sku_master = pd.read_csv(sku_master_file)
    pincode_mapping = pd.read_csv(pincode_mapping_file)
    courier_invoice = pd.read_csv(courier_invoice_file)
    courier_company_rates = pd.read_csv(courier_rates_file)

    # Data Cleaning and Merging (as in the base project)
    order_report = order_report.drop(columns=[col for col in order_report.columns if "Unnamed" in col])
    sku_master = sku_master.drop(columns=[col for col in sku_master.columns if "Unnamed" in col])
    pincode_mapping = pincode_mapping.drop(columns=[col for col in pincode_mapping.columns if "Unnamed" in col])

    merged_data = pd.merge(order_report.rename(columns={'ExternOrderNo': 'Order ID'}), sku_master, on='SKU')
    abc_courier = pincode_mapping.drop_duplicates(subset=['Customer Pincode'])
    courier_abc = courier_invoice[['Order ID', 'Customer Pincode', 'Type of Shipment']]
    pincodes = courier_abc.merge(abc_courier, on='Customer Pincode')
    merged_data = merged_data.merge(pincodes, on='Order ID')

    # Weight calculations
    merged_data['Weights (Kgs)'] = merged_data['Weight (g)'] / 1000

    def weight_slab(weight):
        i = round(weight % 1, 1)
        if i == 0.0:
            return weight
        elif i > 0.5:
            return int(weight) + 1.0
        else:
            return int(weight) + 0.5

    merged_data['Weight Slab As Per ABC'] = merged_data['Weights (Kgs)'].apply(weight_slab)

    # Calculate expected charges
    total_expected_charge = []
    for _, row in merged_data.iterrows():
        fwd_category = 'fwd_' + row['Zone']
        fwd_fixed = courier_company_rates.at[0, fwd_category + '_fixed']
        fwd_additional = courier_company_rates.at[0, fwd_category + '_additional']
        weight_slab = row['Weight Slab As Per ABC']
        additional_weight = max(0, (weight_slab - 0.5) / 0.5)
        total_expected_charge.append(fwd_fixed + additional_weight * fwd_additional)

    merged_data['Expected Charge as per ABC'] = total_expected_charge

    # Calculate differences
    merged_data['Difference (Rs.)'] = courier_invoice['Billing Amount (Rs.)'] - merged_data['Expected Charge as per ABC']

    # --- Advanced Analysis ---

    # Zone-wise Charge Discrepancies
    st.subheader("Zone-wise Charge Discrepancies")
    zone_discrepancy = merged_data.groupby('Zone')['Difference (Rs.)'].mean().reset_index()
    fig_zone_discrepancy = px.bar(zone_discrepancy, x='Zone', y='Difference (Rs.)', title="Average Charge Discrepancy by Zone",
                                  labels={'Difference (Rs.)': 'Average Difference (Rs.)'})
    st.plotly_chart(fig_zone_discrepancy)

    # Shipment Type Analysis
    st.subheader("Shipment Type Analysis")
    shipment_type_summary = merged_data.groupby('Type of Shipment')['Difference (Rs.)'].agg(['mean', 'count']).reset_index()
    fig_shipment_type = px.bar(shipment_type_summary, x='Type of Shipment', y='mean',
                               title="Average Discrepancy by Shipment Type",
                               labels={'mean': 'Average Difference (Rs.)'})
    st.plotly_chart(fig_shipment_type)

    # Weight Slab Distribution
    st.subheader("Weight Slab Distribution")
    weight_distribution = merged_data['Weight Slab As Per ABC'].value_counts().reset_index()
    weight_distribution.columns = ['Weight Slab', 'Count']
    fig_weight_distribution = px.pie(weight_distribution, values='Count', names='Weight Slab',
                                     title="Distribution of Weight Slabs")
    st.plotly_chart(fig_weight_distribution)

    # Overall Summary Table
    st.subheader("Overall Summary Table")

    summary_table = {
        'Metric': ['Total Orders', 'Correctly Charged Orders', 'Overcharged Orders', 'Undercharged Orders'],
        'Value': [
            len(merged_data),
            len(merged_data[merged_data['Difference (Rs.)'] == 0]),
            len(merged_data[merged_data['Difference (Rs.)'] > 0]),
            len(merged_data[merged_data['Difference (Rs.)'] < 0])
        ]
    }

    summary_df = pd.DataFrame(summary_table)
    st.table(summary_df)


    # --- New Feature: Correlation Analysis ---

    st.subheader("Correlation Analysis")

    numeric_columns = ['Weights (Kgs)', 'Expected Charge as per ABC', 'Difference (Rs.)']

    if not numeric_columns:
        st.warning("No numeric columns found for correlation analysis.")

    else:
        correlation_matrix = merged_data[numeric_columns].corr()

        fig_corr, ax_corr = plt.subplots(figsize=(10, 6))
        sns.heatmap(correlation_matrix, annot=True, cmap="coolwarm", ax=ax_corr)
        ax_corr.set_title("Correlation Heatmap")

        st.pyplot(fig_corr)

else:
    st.warning("Please upload all required files to proceed.")
