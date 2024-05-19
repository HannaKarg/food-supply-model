This repository contains the data processing and analysis code on which the paper "How cities source their food: spatial interactions in West African urban food supply" is based. 

PostgreSQL:

The food flow data was manipulated in PostgreSQL for further analysis in QGIS python API and python IDE. For instance, a subset of incoming food flows was created, individual data entries (=trips) were aggregated by city, product and source location, and geographical locations of food sources were joined to the next larger settlement in the Africapolis database and assigned name and population size. The method is described in more detail in the paper and in the SQL script. Result: Food inflow dataset with source settlement characteristics.

QGIS python API:

Apart from the food flow dataset generated in PostgreSQL, the QGIS python API also accesses city-specific location data (a subset of these locations represents food sources). Results from spatial analysis, including suitability averaged over a 50 km buffer around source locations, proximity to roads, spatial category (hinterland source location, other national source location, border settlement, cross-border source location) are based on the city-specific location data. In a next step, these data are joined to the food flow data created in PostgreSQL. Result: City-specific food flow data with spatial characteristics of source locations.

Python IDE:

Here, both the entire food flow dataset and the city-specific flow data are used for further analysis and the generation of figures.
