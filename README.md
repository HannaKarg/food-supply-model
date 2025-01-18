This repository contains the data processing and analysis code on which the paper "Karg, Bellwood-Howard and Ramankutty (2025): How cities source their food: spatial interactions in West African urban food supply" is based. 

PostgreSQL:

The food flow data was processed in PostgreSQL for further analysis in the QGIS python API and python IDE. For instance, a subset of incoming food flows was created, individual data entries (=trips) were aggregated by city, product, and source location, and geographical locations of food sources were joined with the next larger settlement in the Africapolis database and assigned a name and population size. The method is described in more detail in the paper and in the SQL script. Result: Food inflow dataset with source settlement characteristics (InputData/dataset_nodelevel_incoming.csv).

QGIS python API:

In addition to the food flow dataset created in PostgreSQL, the QGIS python API also accesses city-specific location data including geocoded settlements of different sizes (InputData/LocationData/food_flow_locations_...). The results of the spatial analysis, including suitability averaged over a 50 km buffer around the source locations, proximity to roads, spatial category (hinterland, national, border, cross-border) are based on the city-specific location data. In a next step, these data are merged with the food flow data created in PostgreSQL. Result: City-specific food flow data with spatial characteristics of the source locations.

Python IDE:

Here, both sets of data are used for further analysis and to generate figures.
