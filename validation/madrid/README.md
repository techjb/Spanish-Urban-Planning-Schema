# Madrid — validación con 20 parcelas urbanísticas

El 14 de noviembre de 2026 se ejecutó `python validation/madrid/import_plots.py --limit 20` con acceso al [ArcGIS del Ayuntamiento de Madrid](https://sigma.madrid.es/hosted/rest/services/DESARROLLO_URBANO_ACTUALIZADO/USOS_SUELO/MapServer/3). El importador del commit `702eed771ec6cb1e7dae9cfa9240dec5dfc83085` terminó con código 0.

Se comprobaron 20 polígonos con anillos cerrados, 20 identificadores `UBOV_ID` únicos y una correspondencia uno a uno con 20 registros válidos de SUPS Plot 1.0. Por ejemplo, la parcela 6 (etiqueta `M12026`, ámbito `APE.10.22`) corresponde a `MADRID-UBOV-6`.

El GeoJSON conserva el uso principal, el ámbito y la geometría. El campo `ZURV_TX_NOMBRE` llegó vacío en las 20 entidades. Los registros quedaron en `UNKNOWN` con `parameters: {}`. La edificabilidad, ocupación, retranqueos y altura requieren identificar la normativa aplicable a cada parcela.

- [Consulta reproducible y recuento](manifest.json)
- [Entidades municipales](source.geojson)
- [Registros SUPS Plot](sups-plots.json)
- [Importador](import_plots.py)
