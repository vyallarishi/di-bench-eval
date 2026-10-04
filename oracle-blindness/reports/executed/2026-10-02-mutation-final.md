# Dependency mutation score, DI-Bench Python regular, 2026-10-01/02

Runs: mutation 36882143947 (+ range re-run 36904594600), gold 36871839652 (+ 36882158058, 36882329806) on vyallarishi/di-bench-eval.
Gold excludes two instances whose act job never started (kleinanzeigen-bot, wagtail-markdown); harness now fails those.

Gold: 51 of 96 instances pass (0.531)

| Measure | All mutants | Mutants of gold-passing instances |
| --- | --- | --- |
| Deletion mutants | 531 | 233 |
| Deletions that still pass CI | 126 | 115 |
| Dependency mutation score (invisible fraction) | 0.237 | 0.494 |
| Gold-passing instances with at least one invisible dependency | | 38 of 51 |

Invisible dependencies on gold-passing instances:

- KaveIO_PhiK / numpy
- ManiMozaffar_aioclock / pydantic
- MartinThoma_flake8-simplify / flake8
- MartinThoma_flake8-simplify / importlib_metadata
- RhinoSecurityLabs_IAMActionHunter / boto3
- RhinoSecurityLabs_IAMActionHunter / colorama
- RhinoSecurityLabs_IAMActionHunter / policyuniverse
- VikParuchuri_pdftext / pydantic
- VikParuchuri_pdftext / pypdfium2
- abersheeran_kui / typing_extensions
- airbnb_omniduct / lazy_object_proxy
- airbnb_omniduct / packaging
- airbnb_omniduct / python_dateutil
- airbnb_omniduct / wrapt
- bepasty_bepasty-server / markupsafe
- bepasty_bepasty-server / pygments
- bepasty_bepasty-server / werkzeug
- bepasty_bepasty-server / xstatic_jquery
- codypiersall_pynng / sniffio
- falcony-io_sqlalchemy-searchable / sqlalchemy
- fortalice_bofhound / cffi
- fortalice_bofhound / chardet
- fortalice_bofhound / click
- fortalice_bofhound / cryptography
- fortalice_bofhound / dnspython
- fortalice_bofhound / flask
- fortalice_bofhound / future
- fortalice_bofhound / impacket
- fortalice_bofhound / itsdangerous
- fortalice_bofhound / jinja2
- fortalice_bofhound / ldap3
- fortalice_bofhound / ldapdomaindump
- fortalice_bofhound / markupsafe
- fortalice_bofhound / pyasn1
- fortalice_bofhound / pycparser
- fortalice_bofhound / pycryptodomex
- fortalice_bofhound / pyopenssl
- fortalice_bofhound / six
- fortalice_bofhound / typer
- fortalice_bofhound / werkzeug
- google-research_cascades / jax
- humanlayer_humanlayer / click
- humanlayer_humanlayer / requests
- inducer_cgen / numpy
- instadeepai_flashbax / chex
- instadeepai_flashbax / jax
- instadeepai_flashbax / jaxlib
- instadeepai_flashbax / numpy
- instadeepai_flashbax / tensorstore
- instadeepai_flashbax / typing_extensions
- iterative_dvclive / dvc_render
- iterative_dvclive / dvc_studio_client
- iterative_dvclive / funcy
- iterative_dvclive / gto
- iterative_dvclive / psutil
- iterative_dvclive / ruamel_yaml
- iterative_dvclive / scmrepo
- jazzband_django-cookie-consent / django
- jazzband_django-revproxy / django
- jboynyc_textnets / concepts
- jboynyc_textnets / cython
- jboynyc_textnets / igraph
- jboynyc_textnets / pyarrow
- jboynyc_textnets / pycairo
- jboynyc_textnets / setuptools
- jboynyc_textnets / spacy
- jboynyc_textnets / spacy_lookups_data
- jboynyc_textnets / tqdm
- jboynyc_textnets / wasabi
- jleclanche_python-bna / click
- jupyter_jupyter_console / ipython
- jupyter_jupyter_console / jupyter_client
- jupyter_jupyter_console / jupyter_core
- jupyter_jupyter_console / prompt_toolkit
- jupyter_jupyter_console / pygments
- jupyter_jupyter_console / pyzmq
- jupyter_jupyter_console / traitlets
- kcroker_dpsprep / ocrmypdf
- kcroker_dpsprep / pillow
- kovshenin_sail / cryptography
- kovshenin_sail / decorator
- kovshenin_sail / invoke
- kovshenin_sail / paramiko
- kovshenin_sail / requests
- martenlienen_torchode / sympy
- martenlienen_torchode / torch
- miguelgrinberg_turbo-flask / flask
- mrtolkien_fastapi_simple_security / urllib3
- mwclient_mwclient / requests
- omadson_fuzzy-c-means / numpy
- omadson_fuzzy-c-means / pydantic
- omadson_fuzzy-c-means / tabulate
- omadson_fuzzy-c-means / typer
- pycollada_pycollada / unittest2
- regebro_tzlocal / tzdata
- rskmoi_namedivider-python / numpy
- rskmoi_namedivider-python / typer
- sdv-dev_SDGym / boto3
- sdv-dev_SDGym / botocore
- sdv-dev_SDGym / cloudpickle
- sdv-dev_SDGym / psutil
- sdv-dev_SDGym / rdt
- sdv-dev_SDGym / sdmetrics
- sdv-dev_SDGym / tabulate
- sdv-dev_SDGym / tqdm
- sdv-dev_SDGym / xlsxwriter
- simonw_llm-mlc / httpx
- treebeardtech_nbmake / nbformat
- treebeardtech_nbmake / pygments
- treebeardtech_nbmake / pytest
- umarbutler_semchunk / tqdm
- weblyzard_inscriptis / fastapi
- weblyzard_inscriptis / uvicorn
- xnuinside_omymodels / pydantic
- your-tools_tbump / packaging


## Mechanism behind invisible deletions (gold-passing instances)

| Measure | Value |
| --- | --- |
| Mutants of gold-passing instances | 233 |
| Deletions that still passed CI | 115 (0.494) |
| of which phantom, package installed anyway | 91 |
| of which blind spot, package absent and tests still pass | 24 |
| Blind-spot fraction of all mutants | 0.103 |
| Visible deletions where the package was indeed absent (sanity) | 114 of 118 |
| Instances with at least one blind-spot deletion | 15 of 51 |

| Instance | Mutants | Phantom | Blind spot |
| --- | --- | --- | --- |
| jboynyc_textnets | 15 | 5 | 5 |
| RhinoSecurityLabs_IAMActionHunter | 4 | 0 | 3 |
| airbnb_omniduct | 12 | 1 | 3 |
| sdv-dev_SDGym | 13 | 7 | 2 |
| MartinThoma_flake8-simplify | 3 | 1 | 1 |
| abersheeran_kui | 3 | 0 | 1 |
| bepasty_bepasty-server | 13 | 3 | 1 |
| fortalice_bofhound | 22 | 19 | 1 |
| kcroker_dpsprep | 7 | 1 | 1 |
| omadson_fuzzy-c-means | 6 | 3 | 1 |
| pycollada_pycollada | 3 | 0 | 1 |
| regebro_tzlocal | 2 | 0 | 1 |
| rskmoi_namedivider-python | 5 | 1 | 1 |
| simonw_llm-mlc | 2 | 0 | 1 |
| weblyzard_inscriptis | 4 | 1 | 1 |
| 5j9_wikitextparser | 2 | 0 | 0 |
| JeroenDelcour_tplot | 3 | 0 | 0 |
| KaveIO_PhiK | 5 | 1 | 0 |
| ManiMozaffar_aioclock | 4 | 1 | 0 |
| TheHive-Project_TheHive4py | 1 | 0 | 0 |
| Tigge_openant | 1 | 0 | 0 |
| VikParuchuri_pdftext | 4 | 2 | 0 |
| alexandru-dinu_igcc | 2 | 0 | 0 |
| asmeurer_removestar | 1 | 0 | 0 |
| codypiersall_pynng | 2 | 1 | 0 |
| csachs_pyproject-flake8 | 2 | 0 | 0 |
| developmentseed_geojson-pydantic | 1 | 0 | 0 |
| falcony-io_sqlalchemy-searchable | 2 | 1 | 0 |
| gforcada_flake8-isort | 2 | 0 | 0 |
| google-research_cascades | 6 | 1 | 0 |
| humanlayer_humanlayer | 5 | 2 | 0 |
| inducer_cgen | 2 | 1 | 0 |
| instadeepai_flashbax | 7 | 6 | 0 |
| iterative_dvclive | 9 | 7 | 0 |
| jazzband_django-cookie-consent | 2 | 1 | 0 |
| jazzband_django-revproxy | 2 | 1 | 0 |
| jleclanche_python-bna | 2 | 1 | 0 |
| john-hen_Flake8-pyproject | 1 | 0 | 0 |
| jupyter_jupyter_console | 8 | 7 | 0 |
| kovshenin_sail | 12 | 5 | 0 |
| m-burst_flake8-pytest-style | 1 | 0 | 0 |
| martenlienen_torchode | 3 | 2 | 0 |
| miguelgrinberg_flask-sock | 2 | 0 | 0 |
| miguelgrinberg_turbo-flask | 2 | 1 | 0 |
| mrtolkien_fastapi_simple_security | 2 | 1 | 0 |
| mwclient_mwclient | 2 | 1 | 0 |
| odashi_davinci-functions | 2 | 0 | 0 |
| treebeardtech_nbmake | 5 | 3 | 0 |
| umarbutler_semchunk | 2 | 1 | 0 |
| xnuinside_omymodels | 5 | 1 | 0 |
| your-tools_tbump | 5 | 1 | 0 |

| Instance | Deleted dependency | Mechanism |
| --- | --- | --- |
| KaveIO_PhiK | numpy | phantom |
| ManiMozaffar_aioclock | pydantic | phantom |
| MartinThoma_flake8-simplify | flake8 | blind spot |
| MartinThoma_flake8-simplify | importlib_metadata | phantom |
| RhinoSecurityLabs_IAMActionHunter | boto3 | blind spot |
| RhinoSecurityLabs_IAMActionHunter | colorama | blind spot |
| RhinoSecurityLabs_IAMActionHunter | policyuniverse | blind spot |
| VikParuchuri_pdftext | pydantic | phantom |
| VikParuchuri_pdftext | pypdfium2 | phantom |
| abersheeran_kui | typing_extensions | blind spot |
| airbnb_omniduct | lazy_object_proxy | blind spot |
| airbnb_omniduct | packaging | phantom |
| airbnb_omniduct | python_dateutil | blind spot |
| airbnb_omniduct | wrapt | blind spot |
| bepasty_bepasty-server | markupsafe | phantom |
| bepasty_bepasty-server | pygments | phantom |
| bepasty_bepasty-server | werkzeug | phantom |
| bepasty_bepasty-server | xstatic_jquery | blind spot |
| codypiersall_pynng | sniffio | phantom |
| falcony-io_sqlalchemy-searchable | sqlalchemy | phantom |
| fortalice_bofhound | cffi | phantom |
| fortalice_bofhound | chardet | phantom |
| fortalice_bofhound | click | phantom |
| fortalice_bofhound | cryptography | phantom |
| fortalice_bofhound | dnspython | phantom |
| fortalice_bofhound | flask | phantom |
| fortalice_bofhound | future | phantom |
| fortalice_bofhound | impacket | phantom |
| fortalice_bofhound | itsdangerous | phantom |
| fortalice_bofhound | jinja2 | phantom |
| fortalice_bofhound | ldap3 | phantom |
| fortalice_bofhound | ldapdomaindump | phantom |
| fortalice_bofhound | markupsafe | phantom |
| fortalice_bofhound | pyasn1 | phantom |
| fortalice_bofhound | pycparser | phantom |
| fortalice_bofhound | pycryptodomex | phantom |
| fortalice_bofhound | pyopenssl | phantom |
| fortalice_bofhound | six | phantom |
| fortalice_bofhound | typer | blind spot |
| fortalice_bofhound | werkzeug | phantom |
| google-research_cascades | jax | phantom |
| humanlayer_humanlayer | click | phantom |
| humanlayer_humanlayer | requests | phantom |
| inducer_cgen | numpy | phantom |
| instadeepai_flashbax | chex | phantom |
| instadeepai_flashbax | jax | phantom |
| instadeepai_flashbax | jaxlib | phantom |
| instadeepai_flashbax | numpy | phantom |
| instadeepai_flashbax | tensorstore | phantom |
| instadeepai_flashbax | typing_extensions | phantom |
| iterative_dvclive | dvc_render | phantom |
| iterative_dvclive | dvc_studio_client | phantom |
| iterative_dvclive | funcy | phantom |
| iterative_dvclive | gto | phantom |
| iterative_dvclive | psutil | phantom |
| iterative_dvclive | ruamel_yaml | phantom |
| iterative_dvclive | scmrepo | phantom |
| jazzband_django-cookie-consent | django | phantom |
| jazzband_django-revproxy | django | phantom |
| jboynyc_textnets | concepts | blind spot |
| jboynyc_textnets | cython | blind spot |
| jboynyc_textnets | igraph | phantom |
| jboynyc_textnets | pyarrow | blind spot |
| jboynyc_textnets | pycairo | blind spot |
| jboynyc_textnets | setuptools | phantom |
| jboynyc_textnets | spacy | phantom |
| jboynyc_textnets | spacy_lookups_data | blind spot |
| jboynyc_textnets | tqdm | phantom |
| jboynyc_textnets | wasabi | phantom |
| jleclanche_python-bna | click | phantom |
| jupyter_jupyter_console | ipython | phantom |
| jupyter_jupyter_console | jupyter_client | phantom |
| jupyter_jupyter_console | jupyter_core | phantom |
| jupyter_jupyter_console | prompt_toolkit | phantom |
| jupyter_jupyter_console | pygments | phantom |
| jupyter_jupyter_console | pyzmq | phantom |
| jupyter_jupyter_console | traitlets | phantom |
| kcroker_dpsprep | ocrmypdf | blind spot |
| kcroker_dpsprep | pillow | phantom |
| kovshenin_sail | cryptography | phantom |
| kovshenin_sail | decorator | phantom |
| kovshenin_sail | invoke | phantom |
| kovshenin_sail | paramiko | phantom |
| kovshenin_sail | requests | phantom |
| martenlienen_torchode | sympy | phantom |
| martenlienen_torchode | torch | phantom |
| miguelgrinberg_turbo-flask | flask | phantom |
| mrtolkien_fastapi_simple_security | urllib3 | phantom |
| mwclient_mwclient | requests | phantom |
| omadson_fuzzy-c-means | numpy | phantom |
| omadson_fuzzy-c-means | pydantic | phantom |
| omadson_fuzzy-c-means | tabulate | phantom |
| omadson_fuzzy-c-means | typer | blind spot |
| pycollada_pycollada | unittest2 | blind spot |
| regebro_tzlocal | tzdata | blind spot |
| rskmoi_namedivider-python | numpy | phantom |
| rskmoi_namedivider-python | typer | blind spot |
| sdv-dev_SDGym | boto3 | phantom |
| sdv-dev_SDGym | botocore | phantom |
| sdv-dev_SDGym | cloudpickle | phantom |
| sdv-dev_SDGym | psutil | phantom |
| sdv-dev_SDGym | rdt | phantom |
| sdv-dev_SDGym | sdmetrics | phantom |
| sdv-dev_SDGym | tabulate | blind spot |
| sdv-dev_SDGym | tqdm | phantom |
| sdv-dev_SDGym | xlsxwriter | blind spot |
| simonw_llm-mlc | httpx | blind spot |
| treebeardtech_nbmake | nbformat | phantom |
| treebeardtech_nbmake | pygments | phantom |
| treebeardtech_nbmake | pytest | phantom |
| umarbutler_semchunk | tqdm | phantom |
| weblyzard_inscriptis | fastapi | phantom |
| weblyzard_inscriptis | uvicorn | blind spot |
| xnuinside_omymodels | pydantic | phantom |
| your-tools_tbump | packaging | phantom |


## Recovered Qwen-7B vs honest gold
Gold: 51 of 96 instances pass (0.531)

| Measure | All instances | Gold-passing instances only |
| --- | --- | --- |
| Instances | 95 | 50 |
| Execution pass | 6 | 5 |
| Execution pass rate | 0.063 | 0.100 |

Model failures on instances where gold also fails (uninformative): 44

