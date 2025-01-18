import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.formula.api import ols
from statsmodels.graphics.api import interaction_plot, abline_plot
from statsmodels.stats.anova import anova_lm
from statsmodels.api import add_constant
from scipy.stats import pearsonr
from scipy import stats
import os.path
from os import path
import copy
from matplotlib import rcParams
import matplotlib.colors as mcolors
import io
import math



##data

myDir="/my_Directory/"
myDirOutput="/my_OutputDirectory/"
myDirFigures="/my_FiguresDirectory/"

food_flow_commodity_df=pd.read_csv(myDir+"food_flow_commodity_list.csv", delimiter=";")

# Dataset_nodelevel_incoming exported from PostgreSQL

file_path=myDirOutput+'Flow_data/dataset_nodelevel_incoming.csv'

df=pd.read_csv(file_path, delimiter=";", encoding='cp1252')

df['season']=df['season'].str.strip()
df['commodity_name_gen']=df['commodity_name_gen'].str.strip()
df['city']=df['city'].str.strip()

# extract selected commodities

commodity_list=['Maize', 'Millet', 'Pulses', 'Groundnut', 'Yam', 'Plantain','Sorghum','Tomato','Cabbage', 'Eggplant', 'Watermelon', 'Orange', 'Banana', 'Cattle', 'Sheep']

df=df[df['commodity_name_gen'].isin(commodity_list)]

# extract data from main harvest season

df=df[((df['season']=='peak') & (df['city']=='Ouagadougou')) | ((df['season']=='peak') & (df['city']=='Bamako')) | ((df['season']=='lean') & (df['city']=='Bamenda')) | ((df['season']=='peak') & (df['year']==2014) & (df['city']=='Tamale'))]

# compute natural log of distance (km) and node size (no of people)

df.insert(len(df.columns), 'log_distance_km', np.log(df['distance_to_source_km']))
df.insert(len(df.columns), 'log_node_size', np.log(df['node_size']))

# add columns

df["weighted_distance"]=df['distance_to_source_km']*df['percent_of_total_quantity']/100
df["weighted_node_size"]=df['node_size']*df['percent_of_total_quantity']/100
df['weighted_unit_quantity']=df['mean_unit_quantity']*df['percent_of_total_quantity']/100

df['daily_per_cap_quantity_g']=df['daily_quantity']*1000/df['population']

# dataset resulting from spatial analysis (including suitability levels, road access, ..., s. QGIS_python)

city_list=["Bamako", "Ouagadougou", "Tamale", "Bamenda"]
merged_data = []

df.shape[0]


for city in city_list:
    for crop, category in zip(food_flow_commodity_df.commodity_name_gen, food_flow_commodity_df.commodity_category):
        file_path=myDirOutput+f"Flow_data/{city}_{crop}.csv"

        if path.exists(file_path):
            df_sec_data=pd.read_csv(file_path, encoding = "ISO-8859-1")
            df_sec_data['season']=df_sec_data['season'].str.strip()
            if city=="Tamale":
                df_sec_data=df_sec_data[(df_sec_data['season']=='peak') & (df_sec_data['year']==2014)]
            elif city=="Bamako":
                df_sec_data=df_sec_data[df_sec_data['season']=='peak']
            elif city=="Ouagadougou":
                df_sec_data=df_sec_data[df_sec_data['season']=='peak']
            elif city=="Bamenda":
                df_sec_data=df_sec_data[df_sec_data['season']=='lean']

            df_sec_data['per_capita_quantity_g']=df_sec_data['daily_quantity']*1000/df_sec_data['population']

            merged_data.append(df_sec_data)
        else:
            continue

merged_data_all=pd.concat(merged_data)

merged_data_all.shape[0]


## Fig.3: Barplot total inflows

per_cap_quantity_sum=df.groupby(['city','commodity_name_gen', 'season', 'year'], as_index=False)['daily_per_cap_quantity_g'].sum()

# change commodity into categorical to be able to customize order

per_cap_quantity_sum['commodity_name_gen'] = pd.Categorical(per_cap_quantity_sum['commodity_name_gen'], ["Maize", "Millet", "Sorghum", "Groundnut", "Pulses", "Yam", "Plantain", "Tomato", "Cabbage", "Eggplant", "Orange", "Banana", "Watermelon", "Cattle", "Sheep"])

# colour palette

palette = {'Tamale': '#20639B', 'Ouagadougou': '#3CAEA3', 'Bamako': '#F6D55C', 'Bamenda':'#ED553B'}

# barplot

fig, ax = plt.subplots(figsize=(12, 10))
ax.set_facecolor('white')
sns.barplot(data=per_cap_quantity_sum, y='commodity_name_gen', x='daily_per_cap_quantity_g', hue_order = ['Bamako', 'Ouagadougou', 'Tamale', 'Bamenda'], hue='city', palette=palette)
plt.xticks(fontsize=12)
plt.yticks(fontsize=12)
plt.xlabel('Inflows (g/cap/day)',fontsize=12)
plt.ylabel('Commodity',fontsize=12)
plt.grid(axis='x', color='gray', linestyle='dashed')
ax.set_ylabel('Commodity', labelpad=10)
ax.set_xlabel('Inflows (g/cap/day)', labelpad=10)
ax.legend(title='City')
plt.show()
#plt.savefig(myDirFigures+"Fig3.png")



## Fig. 4 and Table S1: Summary table


# assign primary road to intra-regional sources

merged_data_all.loc[merged_data_all.national_origin == 'intraregional', 'prox_to_road'] = 'primary'

# assign primary roads to sources in border regions (outside national boundaries)
merged_data_all.loc[((merged_data_all.NAME_0 != 'Mali') | (merged_data_all.NAME_0 != 'Ghana') | (merged_data_all.NAME_0 != 'Cameroon') | (merged_data_all.NAME_0 != 'Burkina Faso')) &  (merged_data_all.national_origin == 'borderline'), 'prox_to_road'] = 'primary'

# domestic vs import (in %)

df_hinterland=merged_data_all[merged_data_all['distance_to_source_km']<=50]
grp = df_hinterland.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
hinterland_sum=grp['percent_of_total_quantity'].sum()

df_national=merged_data_all[merged_data_all['national_origin']=='national']
grp = df_national.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
national_sum=grp['percent_of_total_quantity'].sum()

df_intraregional=merged_data_all[merged_data_all['national_origin']=='intraregional']
grp = df_intraregional.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
intraregional_sum=grp['percent_of_total_quantity'].sum()

df_border=merged_data_all[merged_data_all['national_origin']=='borderline']
grp = df_border.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
border_sum=grp['percent_of_total_quantity'].sum()

# agricultural suitability (in %)

df_low_suitability=merged_data_all[(merged_data_all['avg_suitability'] >= 7 ) & (merged_data_all['avg_suitability'] < 10 )]
grp = df_low_suitability.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
low_suitability_sum=grp['percent_of_total_quantity'].sum()

df_medium_suitability=merged_data_all[(merged_data_all['avg_suitability'] >= 4 ) & (merged_data_all['avg_suitability'] < 7 )]
grp = df_medium_suitability.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
medium_suitability_sum=grp['percent_of_total_quantity'].sum()

df_high_suitability=merged_data_all[(merged_data_all['avg_suitability'] >= 1 ) & (merged_data_all['avg_suitability'] < 4 )]
grp = df_high_suitability.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
high_suitability_sum=grp['percent_of_total_quantity'].sum()

# distance to road (in %)

df_primary=merged_data_all[merged_data_all['prox_to_road']=='primary']
grp = df_primary.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
primary_sum=grp['percent_of_total_quantity'].sum()

df_secondary=merged_data_all[merged_data_all['prox_to_road']=='secondary']
grp = df_secondary.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
secondary_sum=grp['percent_of_total_quantity'].sum()

df_none=merged_data_all[merged_data_all['prox_to_road']=='none']
grp = df_none.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
none_sum=grp['percent_of_total_quantity'].sum()

# size source settlement (in %)

df_rural=merged_data_all[merged_data_all['node_size']==5000]
grp = df_rural.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
rural_sum=grp['percent_of_total_quantity'].sum()

df_town=merged_data_all[(merged_data_all['node_size']>=10000) & (merged_data_all['node_size']< 100000)]

classification_rural_urban='Urban'
grp = df_town.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
town_sum=grp['percent_of_total_quantity'].sum()

df_city=merged_data_all[merged_data_all['node_size']>=100000]
grp = df_city.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
city_sum=grp['percent_of_total_quantity'].sum()

df_no_data=merged_data_all[merged_data_all['node_size'].isnull()]
grp = df_no_data.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])
no_data_sum=grp['percent_of_total_quantity'].sum()

# concatenate dataframes

grp = merged_data_all.groupby(['city','commodity_name_gen', 'commodity_category', 'season', 'year'])

summary_table=pd.concat([hinterland_sum, national_sum, intraregional_sum, border_sum, low_suitability_sum, medium_suitability_sum, high_suitability_sum, primary_sum, secondary_sum, none_sum, rural_sum, town_sum, city_sum, no_data_sum], axis=1)

summary_table.columns=['hinterland_sum', 'national_sum', 'intraregional_sum', 'border_sum', 'low_suitability_sum', 'medium_suitability_sum', 'high_suitability_sum', 'primary_sum', 'secondary_sum', 'none_sum', 'rural_sum', 'town_sum', 'city_sum', 'no_data_sum']

summary_table.fillna(0, inplace=True)

summary_table['national_wo_hinterland_sum']=summary_table['national_sum']-summary_table['hinterland_sum']

summary_table_list_of_products=summary_table.reset_index()

summary_table_list_of_products['commodity_name_gen'] = pd.Categorical(summary_table_list_of_products['commodity_name_gen'], ['Maize', 'Millet', 'Pulses', 'Groundnut', 'Yam', 'Plantain','Sorghum','Tomato','Cabbage', 'Eggplant', 'Watermelon', 'Orange', 'Banana', 'Cattle', 'Sheep'])

print(summary_table_list_of_products)


# plot: horinzontal stacked bar plot

selected_products=['Maize', 'Millet', 'Groundnut', 'Yam', 'Plantain','Tomato','Eggplant', 'Cabbage', 'Cattle', 'Sheep']

summary_table_selected_products=summary_table.reset_index()

summary_table_selected_products['commodity_name_gen'] = pd.Categorical(summary_table_selected_products['commodity_name_gen'], ['Maize', 'Millet', 'Groundnut', 'Yam', 'Plantain','Tomato','Eggplant', 'Cabbage', 'Cattle', 'Sheep'])

summary_table_selected_products['city'] = pd.Categorical(summary_table_selected_products['city'], ['Bamako', 'Ouagadougou', 'Tamale', 'Bamenda'])

summary_table_selected_products.sort_values(by=['city', 'commodity_name_gen'], ascending=True, inplace=True)

summary_table_selected_products=summary_table_selected_products.loc[summary_table_selected_products['commodity_name_gen'].isin(selected_products)]

palette = {'Tamale': '#20639B', 'Ouagadougou': '#3CAEA3', 'Bamako': '#F6D55C', 'Bamenda':'#ED553B'}

# Spatial category

summary_table_spatial_unit=summary_table_selected_products[['city', 'commodity_name_gen', 'hinterland_sum', 'national_wo_hinterland_sum', 'intraregional_sum', 'border_sum']]

fig, ax = plt.subplots(4, 1, sharex=True, figsize=(2, 8))
for count, city in enumerate(summary_table_spatial_unit['city'].unique()):
    summary_table_spatial_unit_city=summary_table_spatial_unit[summary_table_spatial_unit['city']==city]
    ax[count].set_xlim(0, 100)
    intraregional=summary_table_spatial_unit_city['hinterland_sum']+summary_table_spatial_unit_city['national_wo_hinterland_sum']+summary_table_spatial_unit_city['border_sum']+summary_table_spatial_unit_city['intraregional_sum']
    colour='#20639B'
    sns.barplot(data=summary_table_spatial_unit_city, x=intraregional, y='commodity_name_gen',    label='Intra-regional', ax=ax[count], color=colour)
    border=summary_table_spatial_unit_city['hinterland_sum']+summary_table_spatial_unit_city['national_wo_hinterland_sum']+summary_table_spatial_unit_city['border_sum']
    colour='#ED553B'
    sns.barplot(data=summary_table_spatial_unit_city, x=border, y='commodity_name_gen',    label='Border', ax=ax[count], color=colour)
    national=summary_table_spatial_unit_city['hinterland_sum']+summary_table_spatial_unit_city['national_wo_hinterland_sum']
    colour='#F6D55C'
    sns.barplot(data=summary_table_spatial_unit_city, x=national, y='commodity_name_gen',    label='National', ax=ax[count], color=colour)
    hinterland=summary_table_spatial_unit_city['hinterland_sum']
    colour='#3CAEA3'
    sns.barplot(data=summary_table_spatial_unit_city, x=hinterland, y='commodity_name_gen',    label='Hinterland', ax=ax[count], color=colour)
    ax[count].set_ylabel(city)
    ax[count].get_xaxis().get_label().set_visible(False)
    ax[count].get_yaxis().get_label().set_visible(False)
    ax[count].tick_params(labelleft=True)
    handles, labels = ax[3].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center')
plt.show()
#plt.savefig(myDirFigures+"Fig4_1.png")

# Suitability

summary_table_suitability=summary_table_selected_products[['city', 'commodity_name_gen', 'low_suitability_sum', 'medium_suitability_sum', 'high_suitability_sum']]

fig, ax = plt.subplots(4, 1, sharex=True, figsize=(2, 8))
for count, city in enumerate(summary_table_spatial_unit['city'].unique()):
    summary_table_suitability_city=summary_table_suitability[summary_table_spatial_unit['city']==city]
    ax[count].set_xlim(0, 100)
    high=summary_table_suitability_city['low_suitability_sum']+summary_table_suitability_city['medium_suitability_sum']+summary_table_suitability_city['high_suitability_sum']
    colour='#ED553B'
    sns.barplot(data=summary_table_suitability_city, x=high, y='commodity_name_gen',    ax=ax[count], color=colour, label='High suitability')
    medium=summary_table_suitability_city['low_suitability_sum']+summary_table_suitability_city['medium_suitability_sum']
    colour='#F6D55C'
    sns.barplot(data=summary_table_suitability_city, x=medium, y='commodity_name_gen',    ax=ax[count], color=colour, label='Medium suitability')
    low=summary_table_suitability_city['low_suitability_sum']
    colour='#3CAEA3'
    sns.barplot(data=summary_table_suitability_city, x=low, y='commodity_name_gen',  ax=ax[count], color=colour, label='Low suitability')
    ax[count].get_xaxis().get_label().set_visible(False)
    ax[count].get_yaxis().get_label().set_visible(False)
    ax[count].tick_params(labelleft=False,left=False)
    handles, labels = ax[3].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center')
plt.show()
#plt.savefig(myDirFigures+"Fig4_2.png")

# Road access

summary_table_road_access=summary_table_selected_products[['city', 'commodity_name_gen', 'none_sum', 'secondary_sum', 'primary_sum']]

fig, ax = plt.subplots(4, 1, sharex=True, figsize=(2, 8))
for count, city in enumerate(summary_table_spatial_unit['city'].unique()):
    summary_table_road_access_city=summary_table_road_access[summary_table_road_access['city']==city]
    ax[count].set_xlim(0, 100)
    primary=summary_table_road_access_city['none_sum']+summary_table_road_access_city['secondary_sum']+summary_table_road_access_city['primary_sum']
    colour='#ED553B'
    sns.barplot(data=summary_table_road_access_city, x=primary, y='commodity_name_gen',    ax=ax[count], color=colour, label='Primary road access')
    secondary=summary_table_road_access_city['none_sum']+summary_table_road_access_city['secondary_sum']
    colour='#F6D55C'
    sns.barplot(data=summary_table_road_access_city, x=secondary, y='commodity_name_gen',    ax=ax[count], color=colour, label='Secondary road access')
    none=summary_table_road_access_city['none_sum']
    colour='#3CAEA3'
    sns.barplot(data=summary_table_road_access_city, x=none, y='commodity_name_gen',  ax=ax[count], color=colour, label='None')
    ax[count].get_xaxis().get_label().set_visible(False)
    ax[count].get_yaxis().get_label().set_visible(False)
    ax[count].tick_params(labelleft=False,left=False)
    handles, labels = ax[3].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center')
plt.show()
#plt.savefig(myDirFigures+"Fig4_3.png")

# Settlement type

summary_table_settlement=summary_table_selected_products[['city', 'commodity_name_gen', 'rural_sum', 'town_sum', 'city_sum']]

fig, ax = plt.subplots(4, 1, sharex=True, figsize=(2, 8))
for count, city in enumerate(summary_table_spatial_unit['city'].unique()):
    summary_table_settlement_city=summary_table_settlement[summary_table_settlement['city']==city]
    ax[count].set_xlim(0, 100)
    city=summary_table_settlement_city['rural_sum']+summary_table_settlement_city['town_sum']+summary_table_settlement_city['city_sum']
    colour='#ED553B'
    sns.barplot(data=summary_table_settlement_city, x=city, y='commodity_name_gen',    ax=ax[count], color=colour, label='City')
    town=summary_table_settlement_city['rural_sum']+summary_table_settlement_city['town_sum']
    colour='#F6D55C'
    sns.barplot(data=summary_table_settlement_city, x=town, y='commodity_name_gen',    ax=ax[count], color=colour, label='Town')
    rural=summary_table_settlement_city['rural_sum']
    colour='#3CAEA3'
    sns.barplot(data=summary_table_settlement_city, x=rural, y='commodity_name_gen',  ax=ax[count], color=colour, label='Rural')
    ax[count].get_xaxis().get_label().set_visible(False)
    ax[count].get_yaxis().get_label().set_visible(False)
    ax[count].tick_params(labelleft=False,left=False)
    handles, labels = ax[3].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center')
plt.show()
#plt.savefig(myDirFigures+"Fig4_4.png")

## Table S2: chi2 test

ContingTable=merged_data_all.copy()

commodity_list=['Maize', 'Millet', 'Pulses', 'Groundnut', 'Yam', 'Plantain','Sorghum','Tomato','Cabbage', 'Eggplant', 'Watermelon', 'Orange', 'Banana', 'Cattle', 'Sheep']

ContingTable=ContingTable[ContingTable['commodity_name_gen'].isin(commodity_list)]

# assign primary road to intra-regional sources
ContingTable.loc[ContingTable.national_origin == 'intraregional', 'prox_to_road'] = 'primary'
# assign primary roads to sources in border regions (outside national boundaries)
ContingTable.loc[((ContingTable.NAME_0 != 'Mali') | (ContingTable.NAME_0 != 'Ghana') | (ContingTable.NAME_0 != 'Cameroon') | (ContingTable.NAME_0 != 'Burkina Faso')) &  (ContingTable.national_origin == 'borderline'), 'prox_to_road'] = 'primary'

print(ContingTable)

# domestic vs import
ContingTable.loc[ContingTable.national_origin=='national', 'spatial_unit'] = 'national'
ContingTable.loc[ContingTable.national_origin=='intraregional', 'spatial_unit'] = 'intraregional'
ContingTable.loc[ContingTable.national_origin=='borderline', 'spatial_unit'] = 'border'
ContingTable.loc[ContingTable.distance_to_source_km <=50, 'spatial_unit'] = 'hinterland'

# agricultural suitability
ContingTable.loc[(ContingTable.avg_suitability >= 7) & (ContingTable.avg_suitability < 10), 'agric_suitability'] = 'low'
ContingTable.loc[(ContingTable.avg_suitability >= 4) & (ContingTable.avg_suitability < 7), 'agric_suitability'] = 'medium'
ContingTable.loc[(ContingTable.avg_suitability >= 1) & (ContingTable.avg_suitability < 4), 'agric_suitability'] = 'high'

# size source settlement
ContingTable.loc[ContingTable.node_size ==5000, 'settlement_type'] = 'rural'
ContingTable.loc[(ContingTable.node_size > 5000) & (ContingTable.node_size <= 100000), 'settlement_type'] = 'town'
ContingTable.loc[ContingTable.node_size > 100000, 'settlement_type'] = 'city'

# hinterland
ContingTable.loc[ContingTable.spatial_unit == 'hinterland', 'hinterland_binary'] = 'hinterland'
ContingTable.loc[ContingTable.spatial_unit == 'national', 'hinterland_binary'] = 'no_hinterland'


# Table S2a: interaction between agric_suitability and hinterland

agric_suitability_hinterland= ContingTable.groupby(['agric_suitability','hinterland_binary'], as_index=False)['percent_of_total_quantity'].sum()

contingency_table = pd.crosstab(agric_suitability_hinterland['agric_suitability'], agric_suitability_hinterland['hinterland_binary'], values=agric_suitability_hinterland['percent_of_total_quantity'], aggfunc='sum')
print(contingency_table)

column_names=list(contingency_table.columns.values)
row_names=contingency_table.index.values.tolist()

chi2_results=stats.chi2_contingency(contingency_table, correction=True, lambda_=None)

expected_freq=chi2_results.expected_freq
expected_freq_df = pd.DataFrame(expected_freq, index=row_names,columns= column_names)
print(expected_freq_df)

# Table S2b: interaction between road and hinterland

road_hinterland= ContingTable.groupby(['prox_to_road','hinterland_binary'], as_index=False)['percent_of_total_quantity'].sum()

contingency_table = pd.crosstab(road_hinterland['prox_to_road'], road_hinterland['hinterland_binary'], values=road_hinterland['percent_of_total_quantity'], aggfunc='sum')
print(contingency_table)

column_names=list(contingency_table.columns.values)
row_names=contingency_table.index.values.tolist()

chi2_results=stats.chi2_contingency(contingency_table, correction=True, lambda_=None)

expected_freq=chi2_results.expected_freq
expected_freq_df = pd.DataFrame(expected_freq, index=row_names,columns= column_names)
print(expected_freq_df)

# Table S2c: interaction between settlement_type and hinterland

settlement_type_hinterland= ContingTable.groupby(['settlement_type','hinterland_binary'], as_index=False)['percent_of_total_quantity'].sum()

contingency_table = pd.crosstab(settlement_type_hinterland['settlement_type'], settlement_type_hinterland['hinterland_binary'], values=settlement_type_hinterland['percent_of_total_quantity'], aggfunc='sum')
print(contingency_table)

column_names=list(contingency_table.columns.values)
row_names=contingency_table.index.values.tolist()

chi2_results=stats.chi2_contingency(contingency_table, correction=True, lambda_=None)

expected_freq=chi2_results.expected_freq
expected_freq_df = pd.DataFrame(expected_freq, index=row_names,columns= column_names)
print(expected_freq_df)

# Table S2d: interaction between commodity_category and hinterland

commodity_category_hinterland= ContingTable.groupby(['commodity_category','hinterland_binary'], as_index=False)['percent_of_total_quantity'].sum()

contingency_table = pd.crosstab(commodity_category_hinterland['commodity_category'], commodity_category_hinterland['hinterland_binary'], values=commodity_category_hinterland['percent_of_total_quantity'], aggfunc='sum')
print(contingency_table)

column_names=list(contingency_table.columns.values)
row_names=contingency_table.index.values.tolist()

chi2_results=stats.chi2_contingency(contingency_table, correction=True, lambda_=None)

expected_freq=chi2_results.expected_freq
expected_freq_df = pd.DataFrame(expected_freq, index=row_names,columns= column_names)
print(expected_freq_df)


## Fig. 5 & 6 (scatterplots)

palette_dict = {"city": ["Bamako", "Ouagadougou", "Tamale", "Bamenda"], "city_color": ['#F6D55C', '#3CAEA3', '#20639B', '#ED553B']}
city_list_colors=pd.DataFrame(data=palette_dict)
print(city_list_colors)
category_list=df['commodity_category'].unique().tolist()

    ## Fig. 5
fig, ax = plt.subplots(figsize=(12, 8))

for city, city_color in zip(city_list_colors.city, city_list_colors.city_color):
    df_merge_city=df[df['city']==city]
    sns.regplot(data=df_merge_city, y='log_node_size', x='log_distance_km', ax=ax, label=city, color=city_color)
    plt.xlabel('Distance from supplying settlement (km, log transformed)',fontsize=12)
    plt.ylabel('Supplying settlement size (log transformed)',fontsize=12)
plt.xticks(fontsize=12)
plt.yticks(fontsize=12)
plt.legend()
rcParams.update({'figure.autolayout': True})
plt.tight_layout()
plt.show()
#plt.savefig(myDirFigures+"Fig5.png")

    ## Fig. 6
fig, ax = plt.subplots(figsize=(12, 8))

for city, city_color in zip(city_list_colors.city, city_list_colors.city_color):
    df_merge_city=df[df['city']==city]
    sns.regplot(data=df_merge_city, y='percent_of_total_quantity', x='log_node_size', ax=ax, label=city, color=city_color)
    plt.xlabel('Supplying settlement size (log transformed)',fontsize=12)
    plt.ylabel('Inflow quantity (%)',fontsize=12)
plt.xticks(fontsize=12)
plt.yticks(fontsize=12)
plt.legend()
rcParams.update({'figure.autolayout': True})
plt.tight_layout()
plt.show()
#plt.savefig(myDirFigures+"Fig6.png")

## Linear models

## Table S6a & S7a
# by city
for city in city_list:
    df_merge_city=df[df['city']==city]
    formula='percent_of_total_quantity ~ log_node_size '
    #formula='log_node_size ~  log_distance_km'
    model=smf.ols(formula, data=df_merge_city).fit()
    results_summary=model.summary()
    print(city)
    print(results_summary)

r_square_adjust_list=[]
model_results_list=[]

for city in df['city'].unique():
    df_merge_city=df[df['city']==city]
    formula='percent_of_total_quantity ~  log_node_size'
    #formula='log_node_size ~  log_distance_km'
    model=smf.ols(formula, data=df_merge_city).fit()
    results_summary=model.summary()
    results_as_html = results_summary.tables[1].as_html()
    model_results_table=pd.read_html(results_as_html, header=0, index_col=0)[0]

    model_results_table['city']=city
    model_results_table['variables'] = model_results_table.index.astype(str)
    model_results_list.extend(model_results_table.values.tolist())


model_results_table_merge_all = pd.DataFrame(model_results_list, columns = ['coef', 'std err', 't', 'P>|t|', '[0.025', '0.975]', 'city', 'variable'])
print(model_results_table_merge_all)

## Table S6b & S7b
# by city and crop

r_square_adjust_list=[]
model_results_list=[]

for city in df['city'].unique():
    for crop in commodity_list:
        df_city=df[df['city']==city]
        df_crop=df_city[df_city['commodity_name_gen']==crop]
        if df_crop.empty or df_crop.shape[0]<20:
            continue
        else:
            formula='percent_of_total_quantity ~ log_node_size'
            #formula='log_node_size ~  log_distance_km'
            model=smf.ols(formula, data=df_crop).fit()
            results_summary=model.summary()
            results_as_html = results_summary.tables[1].as_html()
            model_results_table=pd.read_html(results_as_html, header=0, index_col=0)[0]
            model_results_table['city']=city
            model_results_table['crop']=crop
            model_results_table['variables'] = model_results_table.index.astype(str)
            model_results_list.extend(model_results_table.values.tolist())
            r_square_adjust_list.append(city)
            r_square_adjust_list.append(crop)
            r_square_adjust_list.append(model.rsquared_adj)

model_results_table_merge_all = pd.DataFrame(model_results_list, columns = ['coef', 'std err', 't', 'P>|t|', '[0.025', '0.975]', 'city', 'crop', 'variable'])
print(model_results_table_merge_all)

variable_list=model_results_table_merge_all['variable'].unique().tolist()

# r2 adjusted
no_columns=len(r_square_adjust_list)/3
no_columns=int(no_columns)
r_square_adjust_list = np.array(r_square_adjust_list).reshape(no_columns,3)
r_square_adjust=pd.DataFrame(r_square_adjust_list, columns=['city', 'crop', 'rsquared=adj'])


## Fig. S3 & S4: plot data
colors = {'Tamale': '#20639B', 'Ouagadougou': '#3CAEA3', 'Bamako': '#F6D55C', 'Bamenda':'#ED553B'}

for variable in variable_list:
    model_results_extract=model_results_table_merge_all[(model_results_table_merge_all['variable']==variable)]

    model_results=model_results_extract.copy()
    model_results['errors'] = model_results['coef'] - model_results['[0.025']

    crop=model_results['crop']
    coefficient=model_results['coef']
    error=model_results['errors']
    model_results.set_index('crop')

    sns.set_context("poster")

    # Define figure, axes, and plot
    fig, ax = plt.subplots(figsize=(10, 7))

    model_results.plot.barh(x='crop', y='coef',ax=ax, fontsize=15, ecolor=[colors[i] for i in model_results['city']], xerr='errors', color='none', legend=False)

    # Set title & labels
    plt.title(model_results['variable'].iloc[0],fontsize=20)
    ax.set_ylabel('Coefficients',fontsize=13)
    ax.set_yticklabels(crop, rotation=0, fontsize=11)
    ax.set_xlabel('',fontsize=13)

    # Coefficients
    ax.scatter(y=pd.np.arange(model_results.shape[0]), marker='o', s=80, x=model_results['coef'], color=[colors[i] for i in model_results['city']])

    # Line to define zero on the y-axis
    ax.axvline(x=0, linestyle='--', color='red', linewidth=1)
    plt.tight_layout()
    plt.show()
    #plt.savefig(myDirFigures+"FigS4.png")


## standardised matrix (for Fig. 7 and Fig. S5)

# referring to node (=supplying settlement) (mean unit quantity, percent_of_total_connections, percent_of_total_sources)

grp=df.groupby(by=['commodity_name_gen', 'commodity_category', 'season', 'year', 'city']).agg({'percent_of_total_quantity': 'max'})

grp.shape[0]

df_selected_columns=df[['city', 'season', 'year','commodity_name_gen', 'commodity_category', 'source_name','source', 'distance_to_source_km', 'log_distance_km', 'node_size', 'log_node_size', 'percent_of_total_quantity', 'mean_unit_quantity', 'no_connections', 'total_number_connections', 'percent_of_total_connections', 'daily_per_cap_quantity_g', 'daily_quantity']]

dominant_nodes=pd.merge(df_selected_columns, grp, how='inner', on=['city', 'season', 'year', 'commodity_name_gen', 'commodity_category', 'percent_of_total_quantity'])

# referring to supply chain (=aggregated by product and settlement) (weighted distance, weighted node size, weighted unit quantity, number of sources)

weighted_distance_supply_chain=df.groupby(['city', 'season', 'year', 'commodity_name_gen', 'commodity_category'], as_index=False)['weighted_distance'].sum()

weighted_node_size_supply_chain=df.groupby(['city', 'season', 'year', 'commodity_name_gen', 'commodity_category'], as_index=False)['weighted_node_size'].sum()

weighted_unit_quantity_supply_chain=df.groupby(['city', 'season', 'year', 'commodity_name_gen', 'commodity_category'], as_index=False)['weighted_unit_quantity'].sum()

# number of sources

count_sources=df.groupby(['city', 'season', 'year', 'commodity_name_gen', 'commodity_category'], as_index=False)['log_node_size'].count()

count_sources['total_no_sources']=count_sources['log_node_size']

# delete column 'log_node_size'

count_sources.drop(columns='log_node_size', axis=1, inplace=True)

city_list=count_sources['city'].unique().tolist()

# merge

df_no_sources=pd.merge(dominant_nodes, count_sources, how="left", on=['city', 'season', 'year', 'commodity_name_gen', 'commodity_category'])

df_no_sources['percent_of_total_sources']=1/df_no_sources['total_no_sources']*100

df_weighted_dist=pd.merge(df_no_sources, weighted_distance_supply_chain, how="left", on=['city', 'season', 'year', 'commodity_name_gen', 'commodity_category'])

df_weighted_unit_quantity=pd.merge(df_weighted_dist, weighted_unit_quantity_supply_chain, how="left", on=['city', 'season', 'year', 'commodity_name_gen', 'commodity_category'])

df_complete_matrix=pd.merge(df_weighted_unit_quantity, weighted_node_size_supply_chain, how="left", on=['city', 'season', 'year', 'commodity_name_gen', 'commodity_category'])

df_complete_matrix.insert(len(df_complete_matrix.columns), 'log_weighted_distance', np.log(df_complete_matrix['weighted_distance']))

df_complete_matrix.insert(len(df_complete_matrix.columns), 'log_weighted_node_size', np.log(df_complete_matrix['weighted_node_size']))

df_complete_matrix.insert(len(df_complete_matrix.columns), 'log_total_no_sources', np.log(df_complete_matrix['total_no_sources']))

df_complete_matrix.insert(len(df_complete_matrix.columns), 'log_weighted_unit_quantity', np.log(df_complete_matrix['weighted_unit_quantity']))

df_complete_matrix['common_id']=1
grp_matrix = df_complete_matrix.groupby(['common_id'])

## standardising variables
df_complete_matrix['percent_of_total_quantity_std']=grp_matrix['percent_of_total_quantity'].transform('std')
df_complete_matrix['percent_of_total_quantity_mean']=grp_matrix['percent_of_total_quantity'].transform('mean')

df_complete_matrix['total_no_sources_std']=grp_matrix['log_total_no_sources'].transform('std')
df_complete_matrix['total_no_sources_mean']=grp_matrix['log_total_no_sources'].transform('mean')

df_complete_matrix['weighted_distance_std']=grp_matrix['log_weighted_distance'].transform('std')
df_complete_matrix['weighted_distance_mean']=grp_matrix['log_weighted_distance'].transform('mean')

df_complete_matrix['weighted_node_size_std']=grp_matrix['log_weighted_node_size'].transform('std')
df_complete_matrix['weighted_node_size_mean']=grp_matrix['log_weighted_node_size'].transform('mean')

df_complete_matrix['weighted_unit_quantity_std']=grp_matrix['log_weighted_unit_quantity'].transform('std')
df_complete_matrix['weighted_unit_quantity_mean']=grp_matrix['log_weighted_unit_quantity'].transform('mean')

df_complete_matrix['stand_percent_of_total_quantity']=(df_complete_matrix['percent_of_total_quantity']-df_complete_matrix['percent_of_total_quantity_mean'])/df_complete_matrix['percent_of_total_quantity_std']

df_complete_matrix['stand_total_no_sources']=(df_complete_matrix['log_total_no_sources']-df_complete_matrix['total_no_sources_mean'])/df_complete_matrix['total_no_sources_std']

df_complete_matrix['stand_weighted_distance']=(df_complete_matrix['log_weighted_distance']-df_complete_matrix['weighted_distance_mean'])/df_complete_matrix['weighted_distance_std']

df_complete_matrix['stand_weighted_node_size']=(df_complete_matrix['log_weighted_node_size']-df_complete_matrix['weighted_node_size_mean'])/df_complete_matrix['weighted_node_size_std']

df_complete_matrix['stand_weighted_unit_quantity']=(df_complete_matrix['log_weighted_unit_quantity']-df_complete_matrix['weighted_unit_quantity_mean'])/df_complete_matrix['weighted_unit_quantity_std']

df_complete_matrix['combined_scale']=(df_complete_matrix['stand_weighted_unit_quantity']+df_complete_matrix['stand_weighted_node_size']+df_complete_matrix['stand_weighted_distance'])/3


## Fig. S5 (pairplot)

df_matrix_selected_columns=df_complete_matrix[[ 'stand_percent_of_total_quantity', 'stand_total_no_sources', 'stand_weighted_unit_quantity', 'stand_weighted_distance', 'stand_weighted_node_size']]

df_matrix_selected_columns_details=df_complete_matrix[['city', 'commodity_category', 'stand_percent_of_total_quantity', 'stand_total_no_sources', 'stand_weighted_unit_quantity', 'stand_weighted_distance', 'stand_weighted_node_size']]

df_matrix_selected_columns_names=df_matrix_selected_columns_details.copy()

df_matrix_selected_columns_names['Level of concentration']=df_matrix_selected_columns_names['stand_percent_of_total_quantity']
df_matrix_selected_columns_names['Number of source locations']=df_matrix_selected_columns_names['stand_total_no_sources']
df_matrix_selected_columns_names['Transport load']=df_matrix_selected_columns_names['stand_weighted_unit_quantity']
df_matrix_selected_columns_names['Distance from source']=df_matrix_selected_columns_names['stand_weighted_distance']
df_matrix_selected_columns_names['Source settlement size']=df_matrix_selected_columns_names['stand_weighted_node_size']

df_matrix_selected_columns_names.drop(columns=['stand_percent_of_total_quantity', 'stand_total_no_sources', 'stand_weighted_unit_quantity', 'stand_weighted_distance', 'stand_weighted_node_size'], inplace=True)

matplotlib.rc_file_defaults()

def corrfunc(x, y, ax=None, **kws):
    """Plot the correlation coefficient in the top left hand corner of a plot."""
    r, _ = pearsonr(x, y)
    ax = ax or plt.gca()
    ax.annotate(f'ρ = {r:.2f}', xy=(.1, .9), xycoords=ax.transAxes)
sns.set_style(style='white')
pairplot=sns.pairplot(data=df_matrix_selected_columns_names, kind="reg", plot_kws={'scatter_kws': {'s': 4, 'color':'#20639B'}}, diag_kws={'color':'#ED553B'})
pairplot.map_lower(corrfunc)
pairplot.axes[2,0].set_ylim((-2,3))

plt.show()
#plt.savefig(myDirFigures+"FigS5.png")


## Fig. 8

palette = {'Tamale': '#20639B', 'Ouagadougou': '#3CAEA3', 'Bamako': '#F6D55C', 'Bamenda':'#ED553B'}

df_complete_matrix['City']=df_complete_matrix['city']
df_complete_matrix['Average load (t/trip)']=df_complete_matrix['weighted_unit_quantity']/1000

ax=sns.relplot(data=df_complete_matrix, x='percent_of_total_quantity', y='log_weighted_distance', hue_order = ['Bamako', 'Ouagadougou', 'Tamale', 'Bamenda'], hue='City', palette=palette, height=5.5, aspect=1.2, size="Average load (t/trip)", sizes=(5, 300), alpha=.5, legend='brief', edgecolor='gray')

for index, row in df_complete_matrix.iterrows():
    #to avoid overlapping annotations (Bamako Groundnut: 25; Bamako Watermelon: 27; Bamako Orange: 47; Tle Sorghum: 20; Bamenda Cattle (duplicate) & Watermelon: 7, 8)
    if index!=25:
        if index!=7:
            if index!=8:
                if index!=27:
                    if index!=47:
                        if index!=20:
                            plt.annotate(row['commodity_name_gen'], xy=(row['percent_of_total_quantity'], row['log_weighted_distance']), fontsize=7)

plt.ylabel('Distance (km, log)',fontsize=10)
plt.xlabel('Level of concentration (%)',fontsize=10)
plt.xticks(fontsize=10)
plt.yticks(fontsize=10)
plt.axvline(x=45, linewidth=0.5, color='0.5', linestyle='--')
plt.axhline(y=5.2, linewidth=0.5, color='0.5', linestyle='--')
plt.show()
#plt.savefig(myDirFigures+"Fig8.png")


## Interactions (in text)

# origin of flows with access to primary, secondary roads, and with no access

merged_data_all_list_comm=merged_data_all[merged_data_all['commodity_name_gen'].isin(commodity_list)]

sum_per_road_access_city=merged_data_all_list_comm.groupby(['city','prox_to_road'], as_index=False)['daily_quantity'].sum()

print(sum_per_road_access_city)

# origin of flows by settlement types

df_rural=df[df['node_size']==5000].copy()
df_rural['node_class']='Rural'

df_town=df[(df['node_size']>=10000) & (df['node_size']< 100000)].copy()
df_town['node_class']='Town'

df_city=df[df['node_size']>=100000].copy()
df_city['node_class']='City'

df_node_classes=pd.concat([df_rural, df_town, df_city])

sum_per_node_class_city=df_node_classes.groupby(['city', 'node_class'], as_index=False)['daily_quantity'].sum()

sum_per_city=df_node_classes.groupby(['city'], as_index=False)['daily_quantity'].sum()

percent_per_node_class_city=pd.merge(sum_per_node_class_city, sum_per_city, how='inner', on=['city'])

percent_per_node_class_city['percent_per_node_class']=percent_per_node_class_city['daily_quantity_x']*100/percent_per_node_class_city['daily_quantity_y']

print(percent_per_node_class_city)

# mean percent from different nodes classes by commodity (aka interaction node size & crop)

commodity_list1=['Maize','Millet', 'Sorghum', 'Pulses','Groundnut','Yam','Plantain'] # domestic staples; exclue yam and plantain for Ouaga and Bamako

df_node_classes_selected_crops=df_node_classes[df_node_classes['commodity_name_gen'].isin(commodity_list1)]

sum_percent_per_commodity_city=df_node_classes_selected_crops.groupby(['city', 'commodity_name_gen','node_class'], as_index=False)['daily_quantity'].sum()

print(sum_percent_per_commodity_city)

# interaction suitability - distance (Table S3)

merged_data_all_selected_crops=merged_data_all.copy()

    # hinterland

df_hinterland=merged_data_all_selected_crops[merged_data_all_selected_crops['distance_to_source_km']<=50].copy()
df_hinterland['spatial_unit']='Hinterland'
group_hinterland=df_hinterland.groupby(['city','commodity_name_gen', 'spatial_unit'], as_index=False)['daily_quantity'].sum()
df_hinterland_merge=pd.merge(df_hinterland, group_hinterland, how='inner', on=['city', 'commodity_name_gen'])
df_hinterland_merge['spatial_unit_sum']=df_hinterland_merge['daily_quantity_x']*100/df_hinterland_merge['daily_quantity_y']

    # national
df_national=merged_data_all_selected_crops[(merged_data_all_selected_crops['national_origin']=='national') & (merged_data_all_selected_crops['distance_to_source_km']>50)].copy()
df_national['spatial_unit']='National'
group_national=df_national.groupby(['city','commodity_name_gen', 'spatial_unit'], as_index=False)['daily_quantity'].sum()
df_national_merge=pd.merge(df_national, group_national, how='inner', on=['city', 'commodity_name_gen'])
df_national_merge['spatial_unit_sum']=df_national_merge['daily_quantity_x']*100/df_national_merge['daily_quantity_y']

merged_data_all_selected_crops_concat=pd.concat([df_hinterland_merge,df_national_merge])

merged_data_all_selected_crops_concat['weighted_suitability']=merged_data_all_selected_crops_concat['spatial_unit_sum']*merged_data_all_selected_crops_concat['avg_suitability']/100

grp = merged_data_all_selected_crops_concat.groupby(['city','commodity_name_gen', 'spatial_unit_x'], as_index=False)['weighted_suitability'].sum()

print(grp)

interaction=grp.copy()
hinterland_suit=interaction[interaction['spatial_unit_x']=='Hinterland']
hinterland_suit['hinterland_suitability']=hinterland_suit['weighted_suitability']

national_suit=interaction[interaction['spatial_unit_x']=='National']
national_suit['national_suitability']=national_suit['weighted_suitability']

interaction_national_hinterland=pd.merge(hinterland_suit, national_suit, how='inner', on=['city', 'commodity_name_gen'])

interaction_national_hinterland['suitability_difference']=interaction_national_hinterland['national_suitability']-interaction_national_hinterland['hinterland_suitability']

print(interaction_national_hinterland)

# interaction distance and node class (Table S5)

    # spatial units

df_hinterland=merged_data_all_list_comm[merged_data_all_list_comm['distance_to_source_km']<=50].copy()
df_hinterland['spatial_unit']='Hinterland'

df_national=merged_data_all_list_comm[(merged_data_all_list_comm['national_origin']=='national') & (merged_data_all_list_comm['distance_to_source_km']>50)].copy()
df_national['spatial_unit']='National'

merged_data_all_concat=pd.concat([df_hinterland,df_national])

    # node classes
df_rural=merged_data_all_concat[merged_data_all_concat['node_size']==5000].copy()
df_rural['node_class']='Rural'

df_town=merged_data_all_concat[(merged_data_all_concat['node_size']>=10000) & (merged_data_all_concat['node_size']< 100000)].copy()
df_town['node_class']='Town'

df_city=merged_data_all_concat[merged_data_all_concat['node_size']>=100000].copy()
df_city['node_class']='City'

df_node_classes=pd.concat([df_rural, df_town, df_city])

sum_per_spatial_unit_node_class_city=df_node_classes.groupby(['city','spatial_unit', 'node_class'], as_index=False)['daily_quantity'].sum()

print(sum_per_spatial_unit_node_class_city)


# interaction road access and distance (Table S4)

sum_per_road_access_spatial_unit_city=df_node_classes.groupby(['city','prox_to_road', 'spatial_unit'], as_index=False)['daily_quantity'].sum()

print(sum_per_road_access_spatial_unit_city)

sum_per_road_access_spatial_unit_city.to_csv("C:/Users/hanna/Documents/papers/UBC/Outputs/text/model_paper/Proofs/analysis/sum_per_road_access_spatial_unit_city_new.csv")

    # aggregated

sum_per_road_access_city=merged_data_all_list_comm.groupby(['city','prox_to_road'], as_index=False)['daily_quantity'].sum()

print(sum_per_road_access_city)

# average weighted distance by city

df_grp_city_source=df.groupby(['city', 'source', 'distance_to_source_km'],as_index=False)['daily_quantity'].sum()
df_grp_city=df.groupby(['city'],as_index=False)['daily_quantity'].sum()

sum_by_source_city_merge=pd.merge(df_grp_city_source, df_grp_city, how='left', on=['city'])
sum_by_source_city_merge['quantity_percent_per_source']=sum_by_source_city_merge['daily_quantity_x']*100/sum_by_source_city_merge['daily_quantity_y']

sum_by_source_city_merge['weighted_distance_per_city']=sum_by_source_city_merge['distance_to_source_km']*sum_by_source_city_merge['quantity_percent_per_source']/100

print(sum_by_source_city_merge.groupby(['city'],as_index=False)['weighted_distance_per_city'].sum())

