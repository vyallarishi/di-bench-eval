# Hand audit: 40 of 277 pairs (seed 1)

For each pair decide: **GENUINE** (the repository really uses the package on the tested path and a removal is possible), **DOUBTFUL**, or **WRONG** (unwinnable or an artifact). Note the reason in one line.

| # | repository | package | subset | tier | evidence | verdict |
|---|---|---|---|---|---|---|
| 1 | NVIDIA_NVFlare | pyyaml | large | hard | blocked_import_in_repo_frame |  |
| 2 | NVIDIA_NVFlare | protobuf | large | strong | blocked_import_in_repo_frame |  |
| 3 | NVIDIA_NVFlare | requests | large | medium | blocked_import_in_repo_frame |  |
| 4 | NVIDIA_NVFlare | websockets | large | strong | blocked_import_in_repo_frame |  |
| 5 | alexgolec_tda-api | authlib | large | strong | blocked_import_in_repo_frame |  |
| 6 | iterative_dvclive | dvc_render | regular | strong | blocked_import_in_repo_frame |  |
| 7 | jupyter_jupyter_console | jupyter_core | regular | strong | blocked_import_in_repo_frame |  |
| 8 | localstack_localstack | python_dotenv | large | strong | blocked_import_in_repo_frame |  |
| 9 | mu-editor_mu | platformdirs | large | strong | blocked_import_in_repo_frame |  |
| 10 | pyrogram_pyrogram | pyaes | large | strong | blocked_import_in_repo_frame |  |
| 11 | pystorm_streamparse | ruamel_yaml | large | strong | blocked_import_in_repo_frame |  |
| 12 | rskmoi_namedivider-python | numpy | regular | hard | blocked_import_in_repo_frame |  |
| 13 | scikit-learn-contrib_category_encoders | scikit_learn | large | hard | blocked_import_in_repo_frame |  |
| 14 | slackapi_bolt-python | starlette | large | strong | blocked_import_in_repo_frame |  |
| 15 | swirlai_swirl-search | spacy | large | strong | blocked_import_in_repo_frame |  |
| 16 | swirlai_swirl-search | pymongo | large | strong | blocked_import_in_repo_frame |  |
| 17 | aws_chalice | click | large | medium | linter_step_failed |  |
| 18 | aws_chalice | inquirer | large | strong | linter_step_failed |  |
| 19 | kcroker_dpsprep | click | regular | strong | linter_step_failed |  |
| 20 | m-burst_flake8-pytest-style | flake8_plugin_utils | regular | hard | linter_step_failed |  |
| 21 | ManiMozaffar_aioclock | croniter | regular | strong | missing_module_in_repo_frame |  |
| 22 | developmentseed_geojson-pydantic | pydantic | regular | medium | missing_module_in_repo_frame |  |
| 23 | fortalice_bofhound | bloodhound | regular | hard | missing_module_in_repo_frame |  |
| 24 | fortalice_bofhound | rich | regular | strong | missing_module_in_repo_frame |  |
| 25 | humanlayer_humanlayer | python_slugify | regular | strong | missing_module_in_repo_frame |  |
| 26 | humanlayer_humanlayer | python_dotenv | regular | strong | missing_module_in_repo_frame |  |
| 27 | jleclanche_python-bna | pyotp | regular | strong | missing_module_in_repo_frame |  |
| 28 | rskmoi_namedivider-python | pandas | regular | medium | missing_module_in_repo_frame |  |
| 29 | swirlai_swirl-search | pinecone_client | large | indirect | missing_module_in_repo_frame |  |
| 30 | xnuinside_omymodels | table_meta | regular | hard | missing_module_in_repo_frame |  |
| 31 | bepasty_bepasty-server | xstatic_bootstrap | regular | indirect | test_failure_without_import_error |  |
| 32 | bepasty_bepasty-server | xstatic_bootbox | regular | indirect | test_failure_without_import_error |  |
| 33 | bepasty_bepasty-server | xstatic_pygments | regular | indirect | test_failure_without_import_error |  |
| 34 | cowrie_cowrie | tftpy | large | strong | test_failure_without_import_error |  |
| 35 | iterative_dvclive | pynvml | regular | strong | test_failure_without_import_error |  |
| 36 | jboynyc_textnets | cairocffi | regular | indirect | test_failure_without_import_error |  |
| 37 | mu-editor_mu | flake8 | large | indirect | test_failure_without_import_error |  |
| 38 | openvinotoolkit_nncf | openvino_telemetry | large | strong | test_failure_without_import_error |  |
| 39 | swirlai_swirl-search | google_cloud_bigquery | large | indirect | test_failure_without_import_error |  |
| 40 | treebeardtech_nbmake | ipykernel | regular | indirect | test_failure_without_import_error |  |

## 1. NVIDIA_NVFlare / pyyaml  (blocked_import_in_repo_frame, tier hard)

Static footprint:
- `tests/integration_test/generate_all_test_config.py` (test): `import yaml`
- `tests/integration_test/src/utils.py` (test): `import yaml`
- `tests/integration_test/src/provision_site_launcher.py` (test): `import yaml`
- `nvflare/lighter/utils.py`: `import yaml`
- `nvflare/lighter/impl/docker.py`: `import yaml`
- `nvflare/lighter/impl/helm_chart.py`: `import yaml`
- `nvflare/lighter/impl/static_file.py`: `import yaml`
- `nvflare/tool/poc/poc_commands.py`: `import yaml`

Failing CI step: `Run unit test`

Log around the error:

```
nvflare/private/fed/client/client_req_processors.py:19: in <module>
    from .training_cmds import (  # StartClientMGpuProcessor,; SetRunNumberProcessor,
nvflare/private/fed/client/training_cmds.py:23: in <module>
    from nvflare.lighter.utils import verify_folder_signature
nvflare/lighter/utils.py:21: in <module>
    import yaml
conftest.py:18: in find_spec
    raise ImportError(
E   ImportError: No module named 'yaml' (blocked: dependency pyyaml was removed)
```

Verdict: ______  Reason: ______________________________

## 2. NVIDIA_NVFlare / protobuf  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `nvflare/fuel/f3/drivers/grpc/streamer_pb2.py`: `from google.protobuf import descriptor as _descriptor; from google.protobuf import descriptor_pool as _descriptor_pool`
- `nvflare/app_opt/xgboost/histogram_based_v2/proto/federated_pb2.py`: `from google.protobuf import descriptor as _descriptor; from google.protobuf import descriptor_pool as _descriptor_pool`

Failing CI step: `Run unit test`

Log around the error:

```
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <conftest._BlockedFinder object at 0x7f7787883dc0>, fullname = 'google'
path = None, target = None

    def find_spec(self, fullname, path=None, target=None):
        if self._blocked(fullname):
>           raise ImportError(
                "No module named %r (blocked: dependency %s was removed)"
```

Verdict: ______  Reason: ______________________________

## 3. NVIDIA_NVFlare / requests  (blocked_import_in_repo_frame, tier medium)

Static footprint:
- `tests/unit_test/tool/package_checker/utils_test.py` (test): `from requests import Response`
- `nvflare/apis/overseer_spec.py`: `from requests import Response`
- `nvflare/ha/overseer_agent.py`: `from requests import Request, RequestException, Response, Session, codes; from requests.adapters import HTTPAdapter`
- `nvflare/ha/dummy_overseer_agent.py`: `from requests import Response`
- `nvflare/tool/package_checker/utils.py`: `from requests import Request, RequestException, Response, Session, codes; from requests.adapters import HTTPAdapter`

Failing CI step: `Run unit test`

Log around the error:

```
nvflare/private/fed/utils/decomposers/private_decomposers.py:24: in <module>
    from nvflare.private.fed.server.server_state import Cold2HotState, ColdState, Hot2ColdState, HotState, ShutdownState
nvflare/private/fed/server/server_state.py:21: in <module>
    from nvflare.apis.overseer_spec import SP
nvflare/apis/overseer_spec.py:18: in <module>
    from requests import Response
conftest.py:18: in find_spec
    raise ImportError(
E   ImportError: No module named 'requests' (blocked: dependency requests was removed)
```

Verdict: ______  Reason: ______________________________

## 4. NVIDIA_NVFlare / websockets  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `nvflare/fuel/f3/drivers/aio_http_driver.py`: `from websockets.exceptions import ConnectionClosedOK; import websockets`

Failing CI step: `Run unit test`

Log around the error:

```
/opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/importlib/__init__.py:127: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/unit_test/fuel/f3/drivers/driver_manager_test.py:19: in <module>
    from nvflare.fuel.f3.drivers.aio_http_driver import AioHttpDriver
nvflare/fuel/f3/drivers/aio_http_driver.py:18: in <module>
    import websockets
conftest.py:18: in find_spec
    raise ImportError(
E   ImportError: No module named 'websockets' (blocked: dependency websockets was removed)
```

Verdict: ______  Reason: ______________________________

## 5. alexgolec_tda-api / authlib  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `tda/auth.py`: `from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuth2Client`

Failing CI step: `Test with tox py38`

Log around the error:

```
tests/auth_test.py:1: in <module>
    from tda import auth
tda/__init__.py:1: in <module>
    from . import auth
tda/auth.py:4: in <module>
    from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuth2Client
conftest.py:18: in find_spec
    raise ImportError(
E   ImportError: No module named 'authlib' (blocked: dependency authlib was removed)
```

Verdict: ______  Reason: ______________________________

## 6. iterative_dvclive / dvc_render  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `src/dvclive/report.py`: `from dvc_render.html import render_html; from dvc_render.image import ImageRenderer`

Failing CI step: `Run tests`

Log around the error:

```
src/dvclive/__init__.py:1: in <module>
    from .live import Live  # noqa: F401
src/dvclive/live.py:45: in <module>
    from .report import BLANK_NOTEBOOK_REPORT, make_report
src/dvclive/report.py:7: in <module>
    from dvc_render.html import render_html
conftest.py:18: in find_spec
    raise ImportError(
E   ImportError: No module named 'dvc_render' (blocked: dependency dvc_render was removed)
```

Verdict: ______  Reason: ______________________________

## 7. jupyter_jupyter_console / jupyter_core  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `jupyter_console/utils.py`: `from jupyter_core.utils import run_sync as _run_sync, ensure_async`
- `jupyter_console/app.py`: `from jupyter_core.application import JupyterApp, base_aliases, base_flags`

Failing CI step: `Test with pytest`

Log around the error:

```
jupyter_console/ptshell.py:35: in <module>
    from .completer import ZMQCompleter
jupyter_console/completer.py:10: in <module>
    from jupyter_console.utils import run_sync
jupyter_console/utils.py:3: in <module>
    from jupyter_core.utils import run_sync as _run_sync, ensure_async  # noqa
conftest.py:20: in find_spec
    % (fullname, 'jupyter_core')
E   ImportError: No module named 'jupyter_core' (blocked: dependency jupyter_core was removed)
```

Verdict: ______  Reason: ______________________________

## 8. localstack_localstack / python_dotenv  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `localstack-core/localstack/config.py`: `import dotenv`
- `localstack-core/localstack/utils/container_utils/container_client.py`: `import dotenv`

Failing CI step: `Run CLI tests`

Log around the error:

```
  File "/project/localstack-core/localstack/utils/bootstrap.py", line 19, in <module>
    from localstack.utils.container_networking import get_main_container_name
  File "/project/localstack-core/localstack/utils/container_networking.py", line 8, in <module>
    from localstack.utils.container_utils.container_client import ContainerException
  File "/project/localstack-core/localstack/utils/container_utils/container_client.py", line 16, in <module>
    import dotenv
  File "/project/conftest.py", line 18, in find_spec
    raise ImportError(
ImportError: No module named 'dotenv' (blocked: dependency python_dotenv was removed)
```

Verdict: ______  Reason: ______________________________

## 9. mu-editor_mu / platformdirs  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `mu/config.py`: `import platformdirs`
- `mu/logic.py`: `import platformdirs`

Failing CI step: `Run tests`

Log around the error:

```
tests/conftest.py:8: in <module>
    from mu import settings
mu/settings.py:19: in <module>
    from . import config
mu/config.py:3: in <module>
    import platformdirs
conftest.py:20: in find_spec
    % (fullname, 'platformdirs')
E   ImportError: No module named 'platformdirs' (blocked: dependency platformdirs was removed)
```

Verdict: ______  Reason: ______________________________

## 10. pyrogram_pyrogram / pyaes  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `pyrogram/crypto/aes.py`: `import pyaes`

Failing CI step: `Run tests`

Log around the error:

```
pyrogram/connection/transport/tcp/__init__.py:21: in <module>
    from .tcp_abridged_o import TCPAbridgedO
pyrogram/connection/transport/tcp/tcp_abridged_o.py:24: in <module>
    from pyrogram.crypto import aes
pyrogram/crypto/aes.py:52: in <module>
    import pyaes
conftest.py:20: in find_spec
    % (fullname, 'pyaes')
E   ImportError: No module named 'pyaes' (blocked: dependency pyaes was removed)
```

Verdict: ______  Reason: ______________________________

## 11. pystorm_streamparse / ruamel_yaml  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `streamparse/cli/run.py`: `from ruamel import yaml`
- `streamparse/cli/common.py`: `from ruamel import yaml`

Failing CI step: `Test with pytest`

Log around the error:

```
<frozen importlib._bootstrap_external>:843: in exec_module
    ???
<frozen importlib._bootstrap>:219: in _call_with_frames_removed
    ???
streamparse/cli/common.py:8: in <module>
    from ruamel import yaml
sitecustomize.py:18: in find_spec
    raise ImportError(
E   ImportError: No module named 'ruamel' (blocked: dependency ruamel_yaml was removed)
```

Verdict: ______  Reason: ______________________________

## 12. rskmoi_namedivider-python / numpy  (blocked_import_in_repo_frame, tier hard)

Static footprint:
- `tests/test_kanji_statistics.py` (test): `import numpy as np`
- `tests/feature/test_kanji.py` (test): `import numpy as np`
- `tests/feature/test_functional.py` (test): `import numpy as np`
- `tests/feature/test_family_name.py` (test): `import numpy as np`
- `namedivider/kanji_statistics.py`: `import numpy as np; import numpy.typing as npt`
- `namedivider/name_divider.py`: `import numpy as np; import numpy.typing as npt`
- `namedivider/training/kanji_statistics_taker.py`: `import numpy as np`
- `namedivider/divider/name_divider_base.py`: `import numpy as np`
- ... 3 more files

Failing CI step: `Test with pytest`

Log around the error:

```
namedivider/__init__.py:1: in <module>
    from .divider.basic_name_divider import BasicNameDivider
namedivider/divider/basic_name_divider.py:4: in <module>
    from namedivider.divider.name_divider_base import _NameDivider
namedivider/divider/name_divider_base.py:5: in <module>
    import numpy as np
conftest.py:18: in find_spec
    raise ImportError(
E   ImportError: No module named 'numpy' (blocked: dependency numpy was removed)
```

Verdict: ______  Reason: ______________________________

## 13. scikit-learn-contrib_category_encoders / scikit_learn  (blocked_import_in_repo_frame, tier hard)

Static footprint:
- `tests/test_utils.py` (test): `from sklearn import __version__ as skl_version; from sklearn.base import BaseEstimator, TransformerMixin`
- `tests/test_encoders.py` (test): `from sklearn.compose import ColumnTransformer; from sklearn.utils.estimator_checks import check_transformer_general, check_transformers_unfitted, check_n_features_in`
- `tests/test_wrapper.py` (test): `from sklearn.model_selection import GroupKFold`
- `tests/test_feature_names.py` (test): `from sklearn.compose import ColumnTransformer; from sklearn.impute import SimpleImputer`
- `category_encoders/james_stein.py`: `from sklearn.utils.random import check_random_state`
- `category_encoders/wrapper.py`: `from sklearn.base import BaseEstimator, TransformerMixin; from sklearn.model_selection import StratifiedKFold`
- `category_encoders/woe.py`: `from sklearn.utils.random import check_random_state`
- `category_encoders/cat_boost.py`: `from sklearn.utils.random import check_random_state`
- ... 5 more files

Failing CI step: `Test with pytest`

Log around the error:

```
category_encoders/base_contrast_encoder.py:7: in <module>
    from category_encoders.ordinal import OrdinalEncoder
category_encoders/ordinal.py:5: in <module>
    import category_encoders.utils as util
category_encoders/utils.py:8: in <module>
    import sklearn.base
conftest.py:20: in find_spec
    % (fullname, 'scikit_learn')
E   ImportError: No module named 'sklearn' (blocked: dependency scikit_learn was removed)
```

Verdict: ______  Reason: ______________________________

## 14. slackapi_bolt-python / starlette  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `slack_bolt/adapter/starlette/handler.py`: `from starlette.requests import Request; from starlette.responses import Response`
- `slack_bolt/adapter/starlette/async_handler.py`: `from starlette.requests import Request; from starlette.responses import Response`
- `tests/adapter_tests_async/test_async_starlette.py` (test): `from starlette.applications import Starlette; from starlette.requests import Request`
- `tests/adapter_tests_async/test_async_fastapi.py` (test): `from starlette.requests import Request; from starlette.testclient import TestClient`
- `tests/adapter_tests/starlette/test_fastapi.py` (test): `from starlette.requests import Request; from starlette.testclient import TestClient`
- `tests/adapter_tests/starlette/test_starlette.py` (test): `from starlette.applications import Starlette; from starlette.requests import Request`

Failing CI step: `Run tests for HTTP Mode adapters (Starlette)`

Log around the error:

```
/opt/hostedtoolcache/Python/3.6.15/x64/lib/python3.6/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/adapter_tests/starlette/test_fastapi.py:5: in <module>
    from fastapi import FastAPI, Depends
/opt/hostedtoolcache/Python/3.6.15/x64/lib/python3.6/site-packages/fastapi/__init__.py:5: in <module>
    from starlette import status as status
conftest.py:20: in find_spec
    % (fullname, 'starlette')
E   ImportError: No module named 'starlette' (blocked: dependency starlette was removed)
```

Verdict: ______  Reason: ______________________________

## 15. swirlai_swirl-search / spacy  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `swirl/spacy.py`: `import spacy`

Failing CI step: `Run the Unit Tests`

Log around the error:

```
swirl/processors/__init__.py:9: in <module>
    from swirl.processors.dedupe import *
swirl/processors/dedupe.py:8: in <module>
    from swirl.spacy import nlp
swirl/spacy.py:6: in <module>
    import spacy
conftest.py:18: in find_spec
    raise ImportError(
E   ImportError: No module named 'spacy' (blocked: dependency spacy was removed)
```

Verdict: ______  Reason: ______________________________

## 16. swirlai_swirl-search / pymongo  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `swirl/connectors/mongodb.py`: `from pymongo.mongo_client import MongoClient; from pymongo.server_api import ServerApi`

Failing CI step: `Run the Unit Tests`

Log around the error:

```
swirl/tests/microsoft_tests.py:12: in <module>
    from swirl.connectors.microsoft_graph import MicrosoftTeams, M365OutlookMessages
swirl/connectors/__init__.py:19: in <module>
    from swirl.connectors.mongodb import MongoDB
swirl/connectors/mongodb.py:9: in <module>
    from pymongo.mongo_client import MongoClient
conftest.py:18: in find_spec
    raise ImportError(
E   ImportError: No module named 'pymongo' (blocked: dependency pymongo was removed)
```

Verdict: ______  Reason: ______________________________

## 17. aws_chalice / click  (linter_step_failed, tier medium)

Static footprint:
- `tests/unit/test_utils.py` (test): `import click`
- `tests/integration/test_package.py` (test): `from click.testing import CliRunner`
- `tests/functional/cdk/test_construct.py` (test): `from click.testing import CliRunner`
- `tests/functional/cli/test_cli.py` (test): `from click.testing import CliRunner`
- `tests/functional/api/test_package.py` (test): `from click.testing import CliRunner`
- `chalice/utils.py`: `import click`
- `chalice/cli/__init__.py`: `import click`
- `chalice/cli/factory.py`: `import click`

Failing CI step: `Run PRCheck`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.8.18 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmp7w7lfe9n
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (56.0.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (23.0.1)
[Run PR Checks/prcheck]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package
```

Verdict: ______  Reason: ______________________________

## 18. aws_chalice / inquirer  (linter_step_failed, tier strong)

Static footprint:
- `chalice/cli/newproj.py`: `import inquirer`

Failing CI step: `Run PRCheck`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.8.18 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmp1i7s4jqq
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (56.0.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (23.0.1)
[Run PR Checks/prcheck]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package
```

Verdict: ______  Reason: ______________________________

## 19. kcroker_dpsprep / click  (linter_step_failed, tier strong)

Static footprint:
- `dpsprep/dpsprep.py`: `import click`

Failing CI step: `Lint`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.9.25 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmpsg3gx0c5
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/site-packages (79.0.1)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/site-packages (23.0.1)
[Run tests/test]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manage
```

Verdict: ______  Reason: ______________________________

## 20. m-burst_flake8-pytest-style / flake8_plugin_utils  (linter_step_failed, tier hard)

Static footprint:
- `flake8_pytest_style/utils.py`: `from flake8_plugin_utils.utils import is_false, is_none`
- `flake8_pytest_style/plugin.py`: `from flake8_plugin_utils import Plugin`
- `flake8_pytest_style/errors.py`: `from flake8_plugin_utils import Error`
- `flake8_pytest_style/visitors/patch.py`: `from flake8_plugin_utils import Visitor`
- `flake8_pytest_style/visitors/parametrize.py`: `from flake8_plugin_utils import Visitor, check_equivalent_nodes`
- `flake8_pytest_style/visitors/assertion.py`: `from flake8_plugin_utils import Visitor`
- `flake8_pytest_style/visitors/imports.py`: `from flake8_plugin_utils import Visitor`
- `flake8_pytest_style/visitors/fail.py`: `from flake8_plugin_utils import Visitor`
- ... 31 more files

Failing CI step: `Run lint`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.8.18 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmprr8b3jax
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (56.0.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (23.0.1)
[CI/ci]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is 
```

Verdict: ______  Reason: ______________________________

## 21. ManiMozaffar_aioclock / croniter  (missing_module_in_repo_frame, tier strong)

Static footprint:
- `aioclock/triggers.py`: `from croniter import croniter`

Failing CI step: `Run tests`

Log around the error:

```
aioclock/app.py:39: in <module>
    from aioclock.group import Group, Task
aioclock/group.py:17: in <module>
    from aioclock.task import Task
aioclock/task.py:18: in <module>
    from aioclock.triggers import BaseTrigger
aioclock/triggers.py:22: in <module>
    from croniter import croniter
E   ModuleNotFoundError: No module named 'croniter'
```

Verdict: ______  Reason: ______________________________

## 22. developmentseed_geojson-pydantic / pydantic  (missing_module_in_repo_frame, tier medium)

Static footprint:
- `tests/test_features.py` (test): `from pydantic import BaseModel, ValidationError`
- `tests/test_geometries.py` (test): `from pydantic import ValidationError`
- `tests/test_base.py` (test): `from pydantic import Field, ValidationError`
- `geojson_pydantic/features.py`: `from pydantic import BaseModel, Field, StrictInt, StrictStr, field_validator`
- `geojson_pydantic/types.py`: `from pydantic import Field`
- `geojson_pydantic/geometries.py`: `from pydantic import Field, field_validator`
- `geojson_pydantic/base.py`: `from pydantic import BaseModel, SerializationInfo, field_validator, model_serializer`

Failing CI step: `Run tests`

Log around the error:

```
_____________________ ERROR collecting tests/test_base.py ______________________
ImportError while importing test module '/project/tests/test_base.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/importlib/__init__.py:127: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/test_base.py:4: in <module>
    from pydantic import Field, ValidationError
E   ModuleNotFoundError: No module named 'pydantic'
```

Verdict: ______  Reason: ______________________________

## 23. fortalice_bofhound / bloodhound  (missing_module_in_repo_frame, tier hard)

Static footprint:
- `tests/ad/models/test_bloodhound_computer.py` (test): `from bloodhound.enumeration.acls import SecurityDescriptor, ACL, ACCESS_ALLOWED_ACE, ACCESS_MASK, ACE, ACCESS_ALLOWED_OBJECT_ACE, has_extended_right, EXTRIGHTS_GUID_MAPPING, can_write_property, ace_applies`
- `bofhound/parsers/ldap_search_bof.py`: `from bloodhound.ad.utils import ADUtils; from bloodhound.enumeration.acls import ACL, ACCESS_ALLOWED_ACE, ACCESS_MASK, ACE, ACCESS_ALLOWED_OBJECT_ACE, build_relation, has_extended_right, EXTRIGHTS_GUID_MAPPING`
- `bofhound/ad/adds.py`: `from bloodhound.ad.utils import ADUtils; from bloodhound.enumeration.acls import SecurityDescriptor, ACL, ACCESS_ALLOWED_ACE, ACCESS_MASK, ACE, ACCESS_ALLOWED_OBJECT_ACE, has_extended_right, EXTRIGHTS_GUID_MAPPING, can_write_property, ace_applies`
- `bofhound/ad/models/bloodhound_ou.py`: `from bloodhound.ad.utils import ADUtils`
- `bofhound/ad/models/bloodhound_group.py`: `from bloodhound.ad.utils import ADUtils`
- `bofhound/ad/models/bloodhound_user.py`: `from bloodhound.ad.structures import LDAP_SID; from bloodhound.ad.utils import ADUtils`
- `bofhound/ad/models/bloodhound_computer.py`: `from bloodhound.ad.utils import ADUtils, LDAP_SID`
- `bofhound/ad/models/bloodhound_gpo.py`: `from bloodhound.ad.utils import ADUtils`
- ... 3 more files

Failing CI step: `Run test suite`

Log around the error:

```
/usr/local/lib/python3.9/importlib/__init__.py:127: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/ad/test_adds.py:2: in <module>
    from bofhound.ad import ADDS
bofhound/ad/__init__.py:1: in <module>
    from .adds import ADDS
bofhound/ad/adds.py:4: in <module>
    from bloodhound.ad.utils import ADUtils
E   ModuleNotFoundError: No module named 'bloodhound'
```

Verdict: ______  Reason: ______________________________

## 24. fortalice_bofhound / rich  (missing_module_in_repo_frame, tier strong)

Static footprint:
- `bofhound/__init__.py`: `from rich.console import Console`
- `bofhound/logger.py`: `from rich.logging import RichHandler`

Failing CI step: `Run test suite`

Log around the error:

```
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/local/lib/python3.9/importlib/__init__.py:127: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/ad/test_adds.py:2: in <module>
    from bofhound.ad import ADDS
bofhound/__init__.py:1: in <module>
    from rich.console import Console
E   ModuleNotFoundError: No module named 'rich'
```

Verdict: ______  Reason: ______________________________

## 25. humanlayer_humanlayer / python_slugify  (missing_module_in_repo_frame, tier strong)

Static footprint:
- `humanlayer/core/approval.py`: `from slugify import slugify`

Failing CI step: `Test with tox`

Log around the error:

```
==================================== ERRORS ====================================
___________________ ERROR collecting humanlayer/__init__.py ____________________
humanlayer/__init__.py:1: in <module>
    from .core import *
humanlayer/core/__init__.py:1: in <module>
    from .approval import *
humanlayer/core/approval.py:11: in <module>
    from slugify import slugify
E   ModuleNotFoundError: No module named 'slugify'
```

Verdict: ______  Reason: ______________________________

## 26. humanlayer_humanlayer / python_dotenv  (missing_module_in_repo_frame, tier strong)

Static footprint:
- `humanlayer/cli/main.py`: `from dotenv import load_dotenv`

Failing CI step: `Test with tox`

Log around the error:

```
configfile: pyproject.toml
plugins: platformdirs-4.12.2, cov-4.1.0
collected 22 items / 1 error

==================================== ERRORS ====================================
___________________ ERROR collecting humanlayer/cli/main.py ____________________
humanlayer/cli/main.py:4: in <module>
    from dotenv import load_dotenv
E   ModuleNotFoundError: No module named 'dotenv'
```

Verdict: ______  Reason: ______________________________

## 27. jleclanche_python-bna / pyotp  (missing_module_in_repo_frame, tier strong)

Static footprint:
- `bna/cli.py`: `from pyotp import TOTP`
- `bna/utils.py`: `from pyotp import TOTP`
- `tests/test_main.py` (test): `from pyotp import TOTP`

Failing CI step: `Test with pytest`

Log around the error:

```
_____________________ ERROR collecting tests/test_main.py ______________________
ImportError while importing test module '/project/tests/test_main.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.7.17/x64/lib/python3.7/importlib/__init__.py:127: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/test_main.py:5: in <module>
    from pyotp import TOTP
E   ModuleNotFoundError: No module named 'pyotp'
```

Verdict: ______  Reason: ______________________________

## 28. rskmoi_namedivider-python / pandas  (missing_module_in_repo_frame, tier medium)

Static footprint:
- `namedivider/name_divider.py`: `import pandas as pd`
- `namedivider/training/kanji_statistics_taker.py`: `import pandas as pd`
- `namedivider/feature/kanji.py`: `import pandas as pd`

Failing CI step: `Test with pytest`

Log around the error:

```
namedivider/divider/basic_name_divider.py:5: in <module>
    from namedivider.feature.extractor import SimpleFeatureExtractor
namedivider/feature/extractor.py:3: in <module>
    import namedivider.feature.functional as F
namedivider/feature/functional.py:4: in <module>
    from namedivider.feature.kanji import KanjiStatisticsRepository
namedivider/feature/kanji.py:7: in <module>
    import pandas as pd
E   ModuleNotFoundError: No module named 'pandas'
```

Verdict: ______  Reason: ______________________________

## 29. swirlai_swirl-search / pinecone_client  (missing_module_in_repo_frame, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `Run the Unit Tests`

Log around the error:

```
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
swirl/tests/microsoft_tests.py:12: in <module>
    from swirl.connectors.microsoft_graph import MicrosoftTeams, M365OutlookMessages
swirl/connectors/__init__.py:22: in <module>
    from swirl.connectors.pinecone import PineconeDB
swirl/connectors/pinecone.py:20: in <module>
    from pinecone import Pinecone
E   ModuleNotFoundError: No module named 'pinecone'
```

Verdict: ______  Reason: ______________________________

## 30. xnuinside_omymodels / table_meta  (missing_module_in_repo_frame, tier hard)

Static footprint:
- `omymodels/from_ddl.py`: `from table_meta import TableMeta, Type`
- `omymodels/converter.py`: `from table_meta import TableMeta, Type`
- `omymodels/types.py`: `from table_meta.model import Column`
- `omymodels/helpers.py`: `from table_meta import Type`
- `omymodels/models/enum/core.py`: `from table_meta import Type`
- `omymodels/models/sqlalchemy_core/core.py`: `from table_meta.model import Column`
- `omymodels/models/dataclass/core.py`: `from table_meta import TableMeta; from table_meta.model import Column`
- `omymodels/models/sqlmodel/core.py`: `from table_meta.model import Column`
- ... 1 more files

Failing CI step: `Test with pytest`

Log around the error:

```
tests/functional/converter/test_converter.py:2: in <module>
    from helpers import generate_params_for_converter
tests/functional/converter/helpers.py:7: in <module>
    from omymodels import create_models
omymodels/__init__.py:1: in <module>
    from omymodels.converter import convert_models
omymodels/converter.py:4: in <module>
    from table_meta import TableMeta, Type
E   ModuleNotFoundError: No module named 'table_meta'
```

Verdict: ______  Reason: ______________________________

## 31. bepasty_bepasty-server / xstatic_bootstrap  (test_failure_without_import_error, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `run pytest via tox`

Log around the error:

```
Check if Python hostedtoolcache folder exist...
Create Python 3.8.18 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmp05baowu3
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (56.0.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (23.0.1)
[CI/pytest]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It
```

Verdict: ______  Reason: ______________________________

## 32. bepasty_bepasty-server / xstatic_bootbox  (test_failure_without_import_error, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `run pytest via tox`

Log around the error:

```
Check if Python hostedtoolcache folder exist...
Create Python 3.8.18 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmpj9g8zxm2
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (56.0.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (23.0.1)
[CI/pytest]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It
```

Verdict: ______  Reason: ______________________________

## 33. bepasty_bepasty-server / xstatic_pygments  (test_failure_without_import_error, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `run pytest via tox`

Log around the error:

```
Check if Python hostedtoolcache folder exist...
Create Python 3.8.18 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmpl7iv5xnc
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (56.0.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (23.0.1)
[CI/pytest]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It
```

Verdict: ______  Reason: ______________________________

## 34. cowrie_cowrie / tftpy  (test_failure_without_import_error, tier strong)

Static footprint:
- `src/cowrie/commands/tftp.py`: `from tftpy.TftpPacketTypes import TftpPacketDAT, TftpPacketOACK; import tftpy`

Failing CI step: `Test with tox`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.9.25 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmpv8a__1fo
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/site-packages (79.0.1)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/site-packages (23.0.1)
[Tox/build]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It
```

Verdict: ______  Reason: ______________________________

## 35. iterative_dvclive / pynvml  (test_failure_without_import_error, tier strong)

Static footprint:
- `src/dvclive/monitor_system.py`: `from pynvml import nvmlInit, nvmlDeviceGetCount, nvmlDeviceGetHandleByIndex, nvmlDeviceGetMemoryInfo, nvmlDeviceGetUtilizationRates, nvmlShutdown, NVMLError`

Failing CI step: `Run tests`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.9.22 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmp5d6ycdrh
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.9.22/x64/lib/python3.9/site-packages (58.1.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.9.22/x64/lib/python3.9/site-packages (23.0.1)
[Tests/test_core]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manag
```

Verdict: ______  Reason: ______________________________

## 36. jboynyc_textnets / cairocffi  (test_failure_without_import_error, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `Test with pytest`

Log around the error:

```
Check if Python hostedtoolcache folder exist...
Create Python 3.9.25 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmp5qnj737p
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/site-packages (79.0.1)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/site-packages (23.0.1)
[CI/test]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It i
```

Verdict: ______  Reason: ______________________________

## 37. mu-editor_mu / flake8  (test_failure_without_import_error, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `Run tests`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.7.17 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmpdp1lyffc
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.7.17/x64/lib/python3.7/site-packages (47.1.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.7.17/x64/lib/python3.7/site-packages (23.0.1)
[Run tests/Test Py 3.7 - ubuntu-20.04]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the
```

Verdict: ______  Reason: ______________________________

## 38. openvinotoolkit_nncf / openvino_telemetry  (test_failure_without_import_error, tier strong)

Static footprint:
- `nncf/telemetry/wrapper.py`: `from openvino_telemetry import Telemetry`

Failing CI step: `Run common precommit test scope`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.8.18 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmpp8prh2iy
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (56.0.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (23.0.1)
[precommit/common]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package mana
```

Verdict: ______  Reason: ______________________________

## 39. swirlai_swirl-search / google_cloud_bigquery  (test_failure_without_import_error, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `Run the Unit Tests`

Log around the error:

```
Check if Python hostedtoolcache folder exist...
Creating Python hostedtoolcache folder...
Create Python 3.12.4 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmpw5h7agx6
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.12.4/x64/lib/python3.12/site-packages (24.0)
[Test and Build Pipeline/unit-tests]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the s
```

Verdict: ______  Reason: ______________________________

## 40. treebeardtech_nbmake / ipykernel  (test_failure_without_import_error, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `poetry run pytest --cov-report=xml --cov=src`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.8.18 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmppw_2ltlr
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (56.0.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (23.0.1)
[Pytest/pytest]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager
```

Verdict: ______  Reason: ______________________________

