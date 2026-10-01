# Gold and recovered Qwen-7B, DI-Bench Python regular, 2026-10-01

Runs: gold 36871839652 (+ re-runs 36882158058, 36882329806), recovered 36871851223, on vyallarishi/di-bench-eval.

Gold: 52 of 98 instances pass (0.531)

| Measure | All instances | Gold-passing instances only |
| --- | --- | --- |
| Instances | 95 | 51 |
| Execution pass | 6 | 6 |
| Execution pass rate | 0.063 | 0.118 |

Model failures on instances where gold also fails (uninformative): 44


## Gold per-instance
## DI-Bench evaluation summary

| Measure | Value |
| --- | --- |
| Instances with a result | 98 |
| Execution pass | 52 |
| Execution fail | 45 |
| No execution result | 1 |
| Execution pass rate | 0.531 |
| Name-only precision / recall / F1 | 1.000 / 1.000 / 1.000 |

| Instance | Execution | name-only TP / FP / FN |
| --- | --- | --- |
| 5j9_wikitextparser | pass | 2 / 0 / 0 |
| JeroenDelcour_tplot | pass | 3 / 0 / 0 |
| KaveIO_PhiK | pass | 5 / 0 / 0 |
| ManiMozaffar_aioclock | pass | 4 / 0 / 0 |
| MartinThoma_flake8-simplify | pass | 3 / 0 / 0 |
| NabuCasa_hass-nabucasa | fail | 10 / 0 / 0 |
| Quansight_ragna | fail | 18 / 0 / 0 |
| RhinoSecurityLabs_IAMActionHunter | pass | 4 / 0 / 0 |
| Second-Hand-Friends_kleinanzeigen-bot | error | 0 / 0 / 0 |
| TheHive-Project_TheHive4py | pass | 1 / 0 / 0 |
| Tigge_openant | pass | 1 / 0 / 0 |
| VikParuchuri_pdftext | pass | 4 / 0 / 0 |
| WithSecureLabs_IAMSpy | fail | 4 / 0 / 0 |
| Zuehlke_ConfZ | fail | 4 / 0 / 0 |
| abersheeran_kui | pass | 3 / 0 / 0 |
| airbnb_omniduct | pass | 12 / 0 / 0 |
| alexandru-dinu_igcc | pass | 2 / 0 / 0 |
| alteryx_locust-grasshopper | fail | 8 / 0 / 0 |
| asmeurer_removestar | pass | 1 / 0 / 0 |
| bartTC_django-markup | fail | 8 / 0 / 0 |
| behave_behave-django | fail | 3 / 0 / 0 |
| bepasty_bepasty-server | pass | 13 / 0 / 0 |
| codeskyblue_tidevice3 | fail | 9 / 0 / 0 |
| codypiersall_pynng | pass | 2 / 0 / 0 |
| csachs_pyproject-flake8 | pass | 2 / 0 / 0 |
| datnguye_dbterd | fail | 3 / 0 / 0 |
| developmentseed_geojson-pydantic | pass | 1 / 0 / 0 |
| dfm_tinygp | fail | 3 / 0 / 0 |
| epogrebnyak_justpath | fail | 3 / 0 / 0 |
| falcony-io_sqlalchemy-searchable | pass | 2 / 0 / 0 |
| feluelle_airflow-diagrams | fail | 6 / 0 / 0 |
| fortalice_bofhound | pass | 22 / 0 / 0 |
| gandersen101_spaczz | fail | 7 / 0 / 0 |
| gforcada_flake8-isort | pass | 2 / 0 / 0 |
| google-research_cascades | pass | 6 / 0 / 0 |
| graphql-python_graphene-mongo | fail | 5 / 0 / 0 |
| hugovk_pypistats | fail | 7 / 0 / 0 |
| humanlayer_humanlayer | pass | 5 / 0 / 0 |
| ig-python_trading-ig | fail | 8 / 0 / 0 |
| ilcardella_TradingBot | fail | 8 / 0 / 0 |
| inducer_cgen | pass | 2 / 0 / 0 |
| instadeepai_flashbax | pass | 7 / 0 / 0 |
| iterative_dvclive | pass | 9 / 0 / 0 |
| jamesturk_spatula | fail | 7 / 0 / 0 |
| jazzband_django-cookie-consent | pass | 2 / 0 / 0 |
| jazzband_django-revproxy | pass | 2 / 0 / 0 |
| jboynyc_textnets | pass | 15 / 0 / 0 |
| jleclanche_python-bna | pass | 2 / 0 / 0 |
| john-hen_Flake8-pyproject | pass | 2 / 0 / 0 |
| jupyter_jupyter-sphinx | fail | 6 / 0 / 0 |
| jupyter_jupyter_console | pass | 8 / 0 / 0 |
| kcroker_dpsprep | pass | 7 / 0 / 0 |
| kovshenin_sail | pass | 12 / 0 / 0 |
| m-burst_flake8-pytest-style | pass | 1 / 0 / 0 |
| m3dev_gokart | fail | 13 / 0 / 0 |
| martenlienen_torchode | pass | 3 / 0 / 0 |
| mcmtroffaes_sphinxcontrib-bibtex | fail | 6 / 0 / 0 |
| miguelgrinberg_APIFairy | fail | 5 / 0 / 0 |
| miguelgrinberg_flask-sock | pass | 2 / 0 / 0 |
| miguelgrinberg_turbo-flask | pass | 2 / 0 / 0 |
| mixedbread-ai_baguetter | fail | 18 / 0 / 0 |
| mluogh_eastworld | fail | 17 / 0 / 0 |
| mrtolkien_fastapi_simple_security | pass | 2 / 0 / 0 |
| mwclient_mwclient | pass | 2 / 0 / 0 |
| neo4j-contrib_django-neomodel | fail | 2 / 0 / 0 |
| nikdon_pyEntropy | fail | 1 / 0 / 0 |
| odashi_davinci-functions | pass | 2 / 0 / 0 |
| omadson_fuzzy-c-means | pass | 6 / 0 / 0 |
| open2c_bioframe | fail | 8 / 0 / 0 |
| openfoodfacts_openfoodfacts-python | fail | 5 / 0 / 0 |
| orbital-materials_orb-models | fail | 7 / 0 / 0 |
| projectmesa_mesa-geo | fail | 10 / 0 / 0 |
| protectai_modelscan | fail | 6 / 0 / 0 |
| pycollada_pycollada | pass | 3 / 0 / 0 |
| pydantic_bump-pydantic | fail | 4 / 0 / 0 |
| pypa_readme_renderer | fail | 3 / 0 / 0 |
| python-microservices_pyms | fail | 14 / 0 / 0 |
| python-poetry_poetry-plugin-export | fail | 2 / 0 / 0 |
| regebro_tzlocal | pass | 2 / 0 / 0 |
| robot-descriptions_robot_descriptions.py | fail | 2 / 0 / 0 |
| roskakori_pygount | fail | 4 / 0 / 0 |
| royreznik_rexi | fail | 3 / 0 / 0 |
| rskmoi_namedivider-python | pass | 5 / 0 / 0 |
| sabuhish_fastapi-mqtt | fail | 2 / 0 / 0 |
| sdv-dev_SDGym | pass | 18 / 0 / 0 |
| simonw_llm-claude-3 | fail | 2 / 0 / 0 |
| simonw_llm-mlc | pass | 2 / 0 / 0 |
| smagafurov_fastapi-jsonrpc | fail | 4 / 0 / 0 |
| snok_django-auth-adfs | fail | 5 / 0 / 0 |
| staticjinja_staticjinja | fail | 3 / 0 / 0 |
| torchbox_wagtail-markdown | pass | 3 / 0 / 0 |
| treebeardtech_nbmake | pass | 5 / 0 / 0 |
| umarbutler_semchunk | pass | 2 / 0 / 0 |
| valohai_django-allauth-2fa | fail | 4 / 0 / 0 |
| weblyzard_inscriptis | pass | 4 / 0 / 0 |
| whyhow-ai_rule-based-retrieval | fail | 10 / 0 / 0 |
| xnuinside_omymodels | pass | 5 / 0 / 0 |
| your-tools_tbump | pass | 5 / 0 / 0 |


## Recovered per-instance
## DI-Bench evaluation summary

| Measure | Value |
| --- | --- |
| Instances with a result | 95 |
| Execution pass | 6 |
| Execution fail | 89 |
| No execution result | 0 |
| Execution pass rate | 0.063 |
| Name-only precision / recall / F1 | 0.302 / 0.244 / 0.270 |

| Instance | Execution | name-only TP / FP / FN |
| --- | --- | --- |
| 5j9_wikitextparser | fail | 0 / 0 / 2 |
| JeroenDelcour_tplot | fail | 0 / 1 / 3 |
| KaveIO_PhiK | fail | 4 / 3 / 1 |
| ManiMozaffar_aioclock | fail | 0 / 3 / 4 |
| MartinThoma_flake8-simplify | fail | 1 / 1 / 2 |
| NabuCasa_hass-nabucasa | fail | 3 / 36 / 7 |
| Quansight_ragna | fail | 0 / 0 / 18 |
| RhinoSecurityLabs_IAMActionHunter | fail | 2 / 0 / 2 |
| TheHive-Project_TheHive4py | pass | 1 / 4 / 0 |
| Tigge_openant | fail | 0 / 0 / 1 |
| VikParuchuri_pdftext | fail | 1 / 5 / 3 |
| WithSecureLabs_IAMSpy | fail | 0 / 2 / 4 |
| Zuehlke_ConfZ | fail | 2 / 0 / 2 |
| abersheeran_kui | fail | 0 / 7 / 3 |
| airbnb_omniduct | fail | 0 / 0 / 12 |
| alexandru-dinu_igcc | fail | 0 / 0 / 2 |
| asmeurer_removestar | fail | 0 / 3 / 1 |
| bartTC_django-markup | fail | 5 / 1 / 3 |
| behave_behave-django | fail | 2 / 4 / 1 |
| bepasty_bepasty-server | fail | 0 / 0 / 13 |
| codeskyblue_tidevice3 | fail | 1 / 0 / 8 |
| codypiersall_pynng | fail | 1 / 3 / 1 |
| csachs_pyproject-flake8 | fail | 1 / 0 / 1 |
| datnguye_dbterd | fail | 0 / 16 / 3 |
| developmentseed_geojson-pydantic | fail | 1 / 0 / 0 |
| dfm_tinygp | fail | 0 / 0 / 3 |
| epogrebnyak_justpath | fail | 0 / 6 / 3 |
| falcony-io_sqlalchemy-searchable | fail | 1 / 0 / 1 |
| feluelle_airflow-diagrams | fail | 0 / 2 / 6 |
| gandersen101_spaczz | fail | 2 / 2 / 5 |
| gforcada_flake8-isort | fail | 1 / 0 / 1 |
| google-research_cascades | fail | 0 / 1 / 6 |
| graphql-python_graphene-mongo | fail | 0 / 0 / 5 |
| hugovk_pypistats | fail | 0 / 3 / 7 |
| humanlayer_humanlayer | fail | 3 / 0 / 2 |
| ig-python_trading-ig | fail | 1 / 1 / 7 |
| ilcardella_TradingBot | fail | 0 / 0 / 8 |
| inducer_cgen | fail | 1 / 0 / 1 |
| instadeepai_flashbax | fail | 3 / 0 / 4 |
| iterative_dvclive | fail | 0 / 0 / 9 |
| jamesturk_spatula | fail | 1 / 1 / 6 |
| jazzband_django-cookie-consent | fail | 0 / 0 / 2 |
| jazzband_django-revproxy | fail | 1 / 0 / 1 |
| jboynyc_textnets | fail | 1 / 6 / 14 |
| jleclanche_python-bna | pass | 1 / 0 / 1 |
| john-hen_Flake8-pyproject | fail | 1 / 0 / 1 |
| jupyter_jupyter-sphinx | fail | 5 / 34 / 1 |
| jupyter_jupyter_console | fail | 0 / 0 / 8 |
| kcroker_dpsprep | fail | 4 / 1 / 3 |
| kovshenin_sail | fail | 2 / 2 / 10 |
| m-burst_flake8-pytest-style | fail | 0 / 2 / 1 |
| m3dev_gokart | fail | 3 / 15 / 10 |
| martenlienen_torchode | fail | 0 / 0 / 3 |
| mcmtroffaes_sphinxcontrib-bibtex | fail | 1 / 0 / 5 |
| miguelgrinberg_APIFairy | fail | 1 / 2 / 4 |
| miguelgrinberg_flask-sock | pass | 2 / 0 / 0 |
| miguelgrinberg_turbo-flask | fail | 1 / 0 / 1 |
| mixedbread-ai_baguetter | fail | 4 / 11 / 14 |
| mluogh_eastworld | fail | 2 / 2 / 15 |
| mrtolkien_fastapi_simple_security | fail | 1 / 1 / 1 |
| mwclient_mwclient | pass | 2 / 0 / 0 |
| neo4j-contrib_django-neomodel | fail | 2 / 0 / 0 |
| nikdon_pyEntropy | fail | 1 / 0 / 0 |
| odashi_davinci-functions | pass | 2 / 0 / 0 |
| omadson_fuzzy-c-means | fail | 1 / 1 / 5 |
| open2c_bioframe | fail | 2 / 0 / 6 |
| openfoodfacts_openfoodfacts-python | fail | 2 / 0 / 3 |
| orbital-materials_orb-models | fail | 2 / 3 / 5 |
| projectmesa_mesa-geo | fail | 2 / 12 / 8 |
| protectai_modelscan | fail | 0 / 0 / 6 |
| pycollada_pycollada | fail | 0 / 0 / 3 |
| pydantic_bump-pydantic | fail | 1 / 7 / 3 |
| pypa_readme_renderer | fail | 0 / 0 / 3 |
| python-microservices_pyms | fail | 8 / 5 / 6 |
| python-poetry_poetry-plugin-export | fail | 1 / 1 / 1 |
| regebro_tzlocal | fail | 0 / 1 / 2 |
| robot-descriptions_robot_descriptions.py | fail | 0 / 0 / 2 |
| roskakori_pygount | fail | 1 / 8 / 3 |
| royreznik_rexi | fail | 2 / 0 / 1 |
| rskmoi_namedivider-python | fail | 2 / 3 / 3 |
| sabuhish_fastapi-mqtt | fail | 1 / 3 / 1 |
| sdv-dev_SDGym | fail | 4 / 12 / 14 |
| simonw_llm-claude-3 | fail | 2 / 2 / 0 |
| simonw_llm-mlc | fail | 1 / 9 / 1 |
| smagafurov_fastapi-jsonrpc | fail | 1 / 6 / 3 |
| snok_django-auth-adfs | fail | 1 / 2 / 4 |
| staticjinja_staticjinja | fail | 1 / 1 / 2 |
| torchbox_wagtail-markdown | pass | 2 / 2 / 1 |
| treebeardtech_nbmake | fail | 1 / 6 / 4 |
| umarbutler_semchunk | fail | 0 / 0 / 2 |
| valohai_django-allauth-2fa | fail | 2 / 1 / 2 |
| weblyzard_inscriptis | fail | 1 / 1 / 3 |
| whyhow-ai_rule-based-retrieval | fail | 6 / 2 / 4 |
| xnuinside_omymodels | fail | 0 / 0 / 5 |
| your-tools_tbump | fail | 0 / 13 / 5 |

