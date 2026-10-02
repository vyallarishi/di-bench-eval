## Symbol-level reachability (PyCG) against executed deletions

Call graphs built for 18 of 51 gold-passing repos; PyCG failed on 33: KaveIO_PhiK, ManiMozaffar_aioclock, RhinoSecurityLabs_IAMActionHunter, TheHive-Project_TheHive4py, Tigge_openant, VikParuchuri_pdftext, abersheeran_kui, airbnb_omniduct, asmeurer_removestar, bepasty_bepasty-server, codypiersall_pynng, csachs_pyproject-flake8

| Measure | Value |
| --- | --- |
| Declared deps on covered repos with an executed deletion | 45 |
| Symbol-level: used somewhere in the call graph | 40 of 45 (0.89) |
| Symbol-level: reachable from a test | 26 of 45 (0.58) |
| File-level: reachable from a test (previous estimate) | 36 of 45 (0.80) |
| Executed: deletion invisible to CI | 14 of 45 (0.31) |
| Static predictor 'not test-reachable' -> precision for invisibility | 9 of 19 (0.47) |
| Static predictor 'not test-reachable' -> recall of invisible deletions | 9 of 14 (0.64) |
| Deletions CI noticed although the graph saw no test path (graph misses) | 10 |
| Deletions CI missed although the graph saw a test path (phantoms or weak tests) | 5 |

### Used API surface per dependency (difficulty label)

| Surface size (distinct symbols called) | Deps | Deletion invisible |
| --- | --- | --- |
| 0 | 5 | 4 of 5 (0.80) |
| 1 | 17 | 5 of 17 (0.29) |
| 2 to 3 | 5 | 0 of 5 (0.00) |
| 4 to 8 | 10 | 3 of 10 (0.30) |
| 9+ | 8 | 2 of 8 (0.25) |

| Instance | Dependency | Symbols used | Call sites | Test-reachable (symbol) | Test-reachable (file) | Deletion |
| --- | --- | --- | --- | --- | --- | --- |
| 5j9_wikitextparser | regex | 24 | 75 | True | True | fail |
| 5j9_wikitextparser | wcwidth | 1 | 2 | True | True | fail |
| JeroenDelcour_tplot | colorama | 1 | 1 | False | True | fail |
| JeroenDelcour_tplot | numpy | 28 | 37 | True | True | fail |
| JeroenDelcour_tplot | termcolor_whl | 1 | 4 | True | False | fail |
| MartinThoma_flake8-simplify | astor | 2 | 2 | False | True | fail |
| MartinThoma_flake8-simplify | flake8 | 0 | 0 | False | False | pass |
| MartinThoma_flake8-simplify | importlib_metadata | 1 | 1 | False | True | pass |
| alexandru-dinu_igcc | pyyaml | 1 | 1 | False | False | fail |
| alexandru-dinu_igcc | rich | 1 | 8 | False | False | fail |
| developmentseed_geojson-pydantic | pydantic | 11 | 89 | True | True | fail |
| falcony-io_sqlalchemy-searchable | sqlalchemy | 58 | 127 | True | True | pass |
| falcony-io_sqlalchemy-searchable | sqlalchemy_utils | 1 | 8 | True | True | fail |
| inducer_cgen | numpy | 1 | 4 | True | True | pass |
| inducer_cgen | pytools | 2 | 2 | False | True | fail |
| jazzband_django-cookie-consent | django | 85 | 244 | True | True | pass |
| jazzband_django-cookie-consent | django_appconf | 0 | 0 | False | True | fail |
| jleclanche_python-bna | click | 7 | 17 | False | False | pass |
| jleclanche_python-bna | pyotp | 4 | 6 | True | True | fail |
| m-burst_flake8-pytest-style | flake8_plugin_utils | 8 | 107 | True | True | fail |
| mrtolkien_fastapi_simple_security | fastapi | 10 | 11 | True | True | fail |
| mrtolkien_fastapi_simple_security | urllib3 | 0 | 0 | False | False | pass |
| mwclient_mwclient | requests | 1 | 1 | False | True | pass |
| mwclient_mwclient | requests_oauthlib | 1 | 1 | False | True | fail |
| odashi_davinci-functions | dill | 1 | 1 | False | True | fail |
| odashi_davinci-functions | openai | 1 | 4 | False | True | fail |
| rskmoi_namedivider-python | lightgbm | 5 | 5 | True | True | fail |
| rskmoi_namedivider-python | numpy | 7 | 32 | True | True | pass |
| rskmoi_namedivider-python | pandas | 4 | 9 | True | True | fail |
| rskmoi_namedivider-python | regex | 2 | 13 | True | True | fail |
| rskmoi_namedivider-python | typer | 4 | 7 | False | False | pass |
| simonw_llm-mlc | httpx | 0 | 0 | False | False | pass |
| simonw_llm-mlc | llm | 12 | 26 | True | True | fail |
| umarbutler_semchunk | mpire | 1 | 1 | False | True | fail |
| umarbutler_semchunk | tqdm | 1 | 1 | False | True | pass |
| xnuinside_omymodels | jinja2 | 2 | 4 | True | True | fail |
| xnuinside_omymodels | py_models_parser | 1 | 1 | True | True | fail |
| xnuinside_omymodels | pydantic | 0 | 0 | False | False | pass |
| xnuinside_omymodels | simple_ddl_parser | 5 | 5 | True | True | fail |
| xnuinside_omymodels | table_meta | 2 | 4 | True | True | fail |
| your-tools_tbump | cli_ui | 8 | 34 | True | True | fail |
| your-tools_tbump | docopt | 1 | 1 | True | True | fail |
| your-tools_tbump | packaging | 1 | 1 | True | True | pass |
| your-tools_tbump | schema | 6 | 9 | True | True | fail |
| your-tools_tbump | tomlkit | 11 | 30 | True | True | fail |
