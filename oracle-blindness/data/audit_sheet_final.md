# Hand audit: 40 of 355 pairs (seed 1)

For each pair decide: **GENUINE** (the repository really uses the package on the tested path and a removal is possible), **DOUBTFUL**, or **WRONG** (unwinnable or an artifact). Note the reason in one line.

| # | repository | package | subset | tier | evidence | verdict |
|---|---|---|---|---|---|---|
| 1 | AppDaemon_appdaemon | tomli_w | large | strong | blocked_import_in_repo_frame |  |
| 2 | NVIDIA_NVFlare | flask | large | hard | blocked_import_in_repo_frame |  |
| 3 | RhinoSecurityLabs_IAMActionHunter | pandas | regular | strong | blocked_import_in_repo_frame |  |
| 4 | airbnb_omniduct | packaging | regular | strong | blocked_import_in_repo_frame |  |
| 5 | alexgolec_tda-api | authlib | large | strong | blocked_import_in_repo_frame |  |
| 6 | bepasty_bepasty-server | pygments | regular | hard | blocked_import_in_repo_frame |  |
| 7 | falcony-io_sqlalchemy-searchable | sqlalchemy | regular | strong | blocked_import_in_repo_frame |  |
| 8 | humanlayer_humanlayer | pydantic | regular | medium | blocked_import_in_repo_frame |  |
| 9 | itamarst_eliot | boltons | large | strong | blocked_import_in_repo_frame |  |
| 10 | jupyter_jupyter_console | prompt_toolkit | regular | strong | blocked_import_in_repo_frame |  |
| 11 | martenlienen_torchode | sympy | regular | strong | blocked_import_in_repo_frame |  |
| 12 | martenlienen_torchode | torch | regular | hard | blocked_import_in_repo_frame |  |
| 13 | miguelgrinberg_flask-sock | flask | regular | strong | blocked_import_in_repo_frame |  |
| 14 | openvinotoolkit_nncf | packaging | large | medium | blocked_import_in_repo_frame |  |
| 15 | openvinotoolkit_nncf | jsonschema | large | strong | blocked_import_in_repo_frame |  |
| 16 | pystorm_streamparse | pystorm | large | hard | blocked_import_in_repo_frame |  |
| 17 | rskmoi_namedivider-python | regex | regular | hard | blocked_import_in_repo_frame |  |
| 18 | sdv-dev_SDGym | botocore | regular | strong | blocked_import_in_repo_frame |  |
| 19 | sdv-dev_SDGym | tqdm | regular | medium | blocked_import_in_repo_frame |  |
| 20 | slackapi_bolt-python | sanic | large | strong | blocked_import_in_repo_frame |  |
| 21 | slackapi_bolt-python | tornado | large | strong | blocked_import_in_repo_frame |  |
| 22 | slackapi_bolt-python | starlette | large | strong | blocked_import_in_repo_frame |  |
| 23 | slackapi_bolt-python | django | large | strong | blocked_import_in_repo_frame |  |
| 24 | swirlai_swirl-search | google_auth | large | strong | blocked_import_in_repo_frame |  |
| 25 | weblyzard_inscriptis | requests | regular | strong | blocked_import_in_repo_frame |  |
| 26 | your-tools_tbump | packaging | regular | strong | blocked_import_in_repo_frame |  |
| 27 | KaveIO_PhiK | numpy | regular | hard | ci_failure_without_import_error |  |
| 28 | NVIDIA_NVFlare | werkzeug | large | strong | ci_failure_without_import_error |  |
| 29 | aws_chalice | pyyaml | large | strong | ci_failure_without_import_error |  |
| 30 | bepasty_bepasty-server | xstatic_jquery_file_upload | regular | indirect | ci_failure_without_import_error |  |
| 31 | bepasty_bepasty-server | xstatic_bootbox | regular | indirect | ci_failure_without_import_error |  |
| 32 | fortalice_bofhound | pyasn1 | regular | indirect | ci_failure_without_import_error |  |
| 33 | mu-editor_mu | click | large | indirect | ci_failure_without_import_error |  |
| 34 | swirlai_swirl-search | weasel | large | indirect | ci_failure_without_import_error |  |
| 35 | swirlai_swirl-search | pinecone_plugin_interface | large | indirect | ci_failure_without_import_error |  |
| 36 | xnuinside_omymodels | pydantic | regular | indirect | ci_failure_without_import_error |  |
| 37 | instadeepai_flashbax | flax | regular | strong | linter_step_failed |  |
| 38 | kcroker_dpsprep | click | regular | strong | linter_step_failed |  |
| 39 | kcroker_dpsprep | loguru | regular | hard | linter_step_failed |  |
| 40 | openvinotoolkit_nncf | pydot | large | indirect | missing_module_in_repo_frame |  |

## 1. AppDaemon_appdaemon / tomli_w  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `appdaemon/utils.py`: `import tomli_w`

Failing CI step: `Test with pytest`

Log around the error:

```
appdaemon/__main__.py:20: in <module>
    import appdaemon.appdaemon as ad
appdaemon/appdaemon.py:9: in <module>
    import appdaemon.utils as utils
appdaemon/utils.py:27: in <module>
    import tomli_w
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'tomli_w' (blocked: dependency tomli_w was removed)
```

Verdict: ______  Reason: ______________________________

## 2. NVIDIA_NVFlare / flask  (blocked_import_in_repo_frame, tier hard)

Static footprint:
- `nvflare/dashboard/application/users.py`: `from flask import current_app as app; from flask import jsonify, make_response, request`
- `nvflare/dashboard/application/__init__.py`: `from flask import Flask`
- `nvflare/dashboard/application/clients.py`: `from flask import current_app as app; from flask import jsonify, make_response, request`
- `nvflare/dashboard/application/project.py`: `from flask import current_app as app; from flask import jsonify, make_response, request`
- `nvflare/ha/overseer/app.py`: `from flask import Flask`
- `nvflare/ha/overseer/overseer.py`: `from flask import jsonify, request`

Failing CI step: `Run unit test`

Log around the error:

```
/opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/site-packages/_pytest/assertion/rewrite.py:186: in exec_module
    exec(co, module.__dict__)
tests/unit_test/dashboard/conftest.py:20: in <module>
    from nvflare.dashboard.application import init_app
nvflare/dashboard/application/__init__.py:17: in <module>
    from flask import Flask
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'flask' (blocked: dependency flask was removed)
```

Verdict: ______  Reason: ______________________________

## 3. RhinoSecurityLabs_IAMActionHunter / pandas  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `IAMActionHunter/lib/create_csv.py`: `import pandas as pd`

Failing CI step: `Run Python tests`

Log around the error:

```
/opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/importlib/__init__.py:127: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/test_create_csv.py:3: in <module>
    from lib.create_csv import process_json_and_append_to_csv
IAMActionHunter/lib/create_csv.py:1: in <module>
    import pandas as pd
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'pandas' (blocked: dependency pandas was removed)
```

Verdict: ______  Reason: ______________________________

## 4. airbnb_omniduct / packaging  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `omniduct/utils/dependencies.py`: `import packaging.requirements`

Failing CI step: `Run tests`

Log around the error:

```
omniduct/__init__.py:3: in <module>
    from omniduct.duct import Duct
omniduct/duct.py:16: in <module>
    from omniduct.utils.dependencies import check_dependencies
omniduct/utils/dependencies.py:5: in <module>
    import packaging.requirements
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'packaging' (blocked: dependency packaging was removed)
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
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'authlib' (blocked: dependency authlib was removed)
```

Verdict: ______  Reason: ______________________________

## 6. bepasty_bepasty-server / pygments  (blocked_import_in_repo_frame, tier hard)

Static footprint:
- `src/bepasty/apis/lodgeit.py`: `from pygments.lexers import get_all_lexers`
- `src/bepasty/utils/formatters.py`: `from pygments.formatters.html import HtmlFormatter`
- `src/bepasty/utils/upload.py`: `from pygments.lexers import get_lexer_for_filename; from pygments.util import ClassNotFound as NoPygmentsLexer`
- `src/bepasty/views/index.py`: `from pygments.lexers import get_all_lexers`
- `src/bepasty/views/display.py`: `from pygments import highlight; from pygments.lexers import get_lexer_for_mimetype`

Failing CI step: `run pytest via tox`

Log around the error:

```
.tox/py38/lib/python3.8/site-packages/bepasty/app.py:14: in <module>
    from .apis import blueprint as blueprint_apis
.tox/py38/lib/python3.8/site-packages/bepasty/apis/__init__.py:3: in <module>
    from .lodgeit import LodgeitUpload
.tox/py38/lib/python3.8/site-packages/bepasty/apis/lodgeit.py:6: in <module>
    from pygments.lexers import get_all_lexers
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'pygments' (blocked: dependency pygments was removed)
```

Verdict: ______  Reason: ______________________________

## 7. falcony-io_sqlalchemy-searchable / sqlalchemy  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `tests/conftest.py` (test): `from sqlalchemy import Column, create_engine, DateTime, ForeignKey, Integer, String, Text, text; from sqlalchemy.orm import close_all_sessions, configure_mappers, declarative_base, sessionmaker`
- `tests/test_single_table_inheritance.py` (test): `import sqlalchemy as sa`
- `tests/test_weighted_search_vector.py` (test): `from sqlalchemy import text; import sqlalchemy as sa`
- `tests/test_drop_trigger.py` (test): `from sqlalchemy import text`
- `tests/test_sync_trigger.py` (test): `from sqlalchemy import text; import sqlalchemy as sa`
- `tests/schema_test_case.py` (test): `from sqlalchemy import text`
- `tests/test_schema_creation.py` (test): `import sqlalchemy as sa`
- `tests/test_sql_functions.py` (test): `from sqlalchemy import text`
- ... 6 more files

Failing CI step: `Run tests`

Log around the error:

```
py-sqla1.4: freeze> python -m pip freeze --all
py-sqla1.4: greenlet==3.5.6,iniconfig==2.3.0,packaging==26.3,pip==26.2.1,pluggy==1.6.0,psycopg2==2.9.13,Pygments==2.21.0,pytest==9.1.1,SQLAlchemy==1.4.54,sqlalc
py-sqla1.4: commands[0]> py.test
ImportError while loading conftest '/project/tests/conftest.py'.
tests/conftest.py:4: in <module>
    from sqlalchemy import (
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'sqlalchemy' (blocked: dependency sqlalchemy was removed)
```

Verdict: ______  Reason: ______________________________

## 8. humanlayer_humanlayer / pydantic  (blocked_import_in_repo_frame, tier medium)

Static footprint:
- `humanlayer/core/models.py`: `from pydantic import BaseModel`
- `humanlayer/core/cloud.py`: `from pydantic import BaseModel, model_validator`
- `humanlayer/core/approval.py`: `from pydantic import BaseModel`

Failing CI step: `Test with tox`

Log around the error:

```
humanlayer/__init__.py:1: in <module>
    from .core import *
humanlayer/core/__init__.py:1: in <module>
    from .approval import *
humanlayer/core/approval.py:10: in <module>
    from pydantic import BaseModel
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'pydantic' (blocked: dependency pydantic was removed)
```

Verdict: ______  Reason: ______________________________

## 9. itamarst_eliot / boltons  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `eliot/_action.py`: `from boltons.funcutils import wraps`

Failing CI step: `Run tox targets for 3.9`

Log around the error:

```
eliot/__init__.py:8: in <module>
    from ._message import Message
eliot/_message.py:195: in <module>
    from ._action import log_message, TaskLevel
eliot/_action.py:16: in <module>
    from boltons.funcutils import wraps
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'boltons' (blocked: dependency boltons was removed)
```

Verdict: ______  Reason: ______________________________

## 10. jupyter_jupyter_console / prompt_toolkit  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `jupyter_console/ptshell.py`: `from prompt_toolkit import __version__ as ptk_version; from prompt_toolkit.completion import Completer, Completion`

Failing CI step: `Test with pytest`

Log around the error:

```
/opt/hostedtoolcache/Python/3.7.17/x64/lib/python3.7/importlib/__init__.py:127: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
jupyter_console/tests/test_image_handler.py:13: in <module>
    from jupyter_console.ptshell import ZMQTerminalInteractiveShell
jupyter_console/ptshell.py:47: in <module>
    from prompt_toolkit.completion import Completer, Completion
conftest.py:83: in __getattr__
    raise ImportError("cannot use %r: %s" % (real.__name__, _MARK))
E   ImportError: cannot use 'prompt_toolkit.completion': (blocked: dependency prompt_toolkit was removed)
```

Verdict: ______  Reason: ______________________________

## 11. martenlienen_torchode / sympy  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `torchode/single_step_methods/tsit5.py`: `import sympy as sp`

Failing CI step: `Test with pytest`

Log around the error:

```
torchode/adjoints.py:8: in <module>
    from .single_step_methods import SingleStepMethod
torchode/single_step_methods/__init__.py:4: in <module>
    from .tsit5 import Tsit5
torchode/single_step_methods/tsit5.py:3: in <module>
    import sympy as sp
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'sympy' (blocked: dependency sympy was removed)
```

Verdict: ______  Reason: ______________________________

## 12. martenlienen_torchode / torch  (blocked_import_in_repo_frame, tier hard)

Static footprint:
- `torchode/step_size_controllers.py`: `import torch; import torch.nn as nn`
- `torchode/terms.py`: `import torch.nn as nn`
- `torchode/interpolation.py`: `import torch`
- `torchode/adjoints.py`: `import torch; import torch.nn as nn`
- `torchode/interface.py`: `import torch`
- `torchode/typing.py`: `import torch`
- `torchode/single_step_methods/tsit5.py`: `import torch`
- `torchode/single_step_methods/runge_kutta.py`: `import torch; import torch.nn as nn`
- ... 14 more files

Failing CI step: `Test with pytest`

Log around the error:

```
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/importlib/__init__.py:127: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/adjoint_test.py:5: in <module>
    import torch
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'torch' (blocked: dependency torch was removed)
```

Verdict: ______  Reason: ______________________________

## 13. miguelgrinberg_flask-sock / flask  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `tests/test_flask_sock.py` (test): `from flask import Flask, Blueprint`
- `src/flask_sock/__init__.py`: `from flask import Blueprint, request, Response, current_app`

Failing CI step: `tox`

Log around the error:

```
    raise ImportError("No module named %r %s" % (fullname, _MARK))
/project/.tox/py38/lib/python3.8/site-packages/coverage/inorout.py:504: CoverageWarning: Module flask_sock was never imported. (module-not-imported)
  self.warn(f"Module {pkg} was never imported.", slug="module-not-imported")
/project/.tox/py38/lib/python3.8/site-packages/coverage/control.py:894: CoverageWarning: No data was collected. (no-data-collected)
  self._warn("No data was collected.", slug="no-data-collected")
/project/.tox/py38/lib/python3.8/site-packages/pytest_cov/plugin.py:339: CovReportWarning: Failed to generate report: No data to report.

  self.cov_controller.finish()
E   ImportError: No module named 'flask' (blocked: dependency flask was removed)
```

Verdict: ______  Reason: ______________________________

## 14. openvinotoolkit_nncf / packaging  (blocked_import_in_repo_frame, tier medium)

Static footprint:
- `tests/post_training/test_quantize_conformance.py` (test): `from packaging import version`
- `tests/openvino/native/common.py` (test): `from packaging import version`
- `tests/torch/test_sanity_sample.py` (test): `from packaging import version`
- `tests/torch/test_tracing_context.py` (test): `from packaging import version`
- `tests/torch/sparsity/movement/test_training.py` (test): `from packaging import version`
- `tests/torch/sparsity/movement/test_model_saving.py` (test): `from packaging import version`
- `tests/torch/sparsity/movement/test_structured_mask.py` (test): `from packaging import version`
- `tests/torch/nas/test_elastic_depth.py` (test): `from packaging import version`
- ... 7 more files

Failing CI step: `Run common precommit test scope`

Log around the error:

```
nncf/quantization/__init__.py:13: in <module>
    from nncf.quantization.quantize_model import compress_weights as compress_weights
nncf/quantization/quantize_model.py:16: in <module>
    from nncf.common.deprecation import warning_deprecated
nncf/common/deprecation.py:17: in <module>
    from packaging import version
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'packaging' (blocked: dependency packaging was removed)
```

Verdict: ______  Reason: ______________________________

## 15. openvinotoolkit_nncf / jsonschema  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `tests/common/sdl/test_config_schema.py` (test): `import jsonschema`
- `tests/common/sdl/test_schema.py` (test): `import jsonschema`
- `nncf/config/config.py`: `import jsonschema`
- `nncf/config/schema.py`: `import jsonschema`

Failing CI step: `Run common precommit test scope`

Log around the error:

```
nncf/__init__.py:19: in <module>
    from nncf.config import NNCFConfig as NNCFConfig
nncf/config/__init__.py:14: in <module>
    from nncf.config.config import NNCFConfig as NNCFConfig
nncf/config/config.py:16: in <module>
    import jsonschema
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'jsonschema' (blocked: dependency jsonschema was removed)
```

Verdict: ______  Reason: ______________________________

## 16. pystorm_streamparse / pystorm  (blocked_import_in_repo_frame, tier hard)

Static footprint:
- `streamparse/run.py`: `from pystorm.component import _SERIALIZERS`
- `streamparse/storm/bolt.py`: `import pystorm`
- `streamparse/storm/__init__.py`: `from pystorm import Tuple`
- `streamparse/storm/spout.py`: `import pystorm`
- `streamparse/storm/component.py`: `from pystorm.component import StormHandler; import pystorm`
- `streamparse/dsl/topology.py`: `from pystorm.component import Component`

Failing CI step: `Test with pytest`

Log around the error:

```
streamparse/__init__.py:9: in <module>
    from . import bolt, cli, component, dsl, spout, storm
streamparse/bolt.py:5: in <module>
    from .storm.bolt import *
streamparse/storm/__init__.py:5: in <module>
    from pystorm import Tuple
sitecustomize.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'pystorm' (blocked: dependency pystorm was removed)
```

Verdict: ______  Reason: ______________________________

## 17. rskmoi_namedivider-python / regex  (blocked_import_in_repo_frame, tier hard)

Static footprint:
- `namedivider/name_divider.py`: `import regex`
- `namedivider/training/kanji_statistics_taker.py`: `import regex`
- `namedivider/rule/kanji_kana_rule.py`: `import regex`
- `namedivider/divider/name_divider_base.py`: `import regex`
- `namedivider/beta_bert_divider/combined_name_divider.py`: `import regex`

Failing CI step: `Test with pytest`

Log around the error:

```
namedivider/__init__.py:1: in <module>
    from .divider.basic_name_divider import BasicNameDivider
namedivider/divider/basic_name_divider.py:4: in <module>
    from namedivider.divider.name_divider_base import _NameDivider
namedivider/divider/name_divider_base.py:6: in <module>
    import regex
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'regex' (blocked: dependency regex was removed)
```

Verdict: ______  Reason: ______________________________

## 18. sdv-dev_SDGym / botocore  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `sdgym/s3.py`: `import botocore`
- `tests/unit/test_datasets.py` (test): `import botocore`

Failing CI step: `Run unit tests`

Log around the error:

```
name = 'config'

    def __getattr__(self, name):
        real = object.__getattribute__(self, "_real")
        if name.startswith("__") and name.endswith("__"):
            return getattr(real, name)
        if _repo_origin():
>           raise ImportError("cannot use %r: %s" % (real.__name__, _MARK))
E           ImportError: cannot use 'botocore': (blocked: dependency botocore was removed)
```

Verdict: ______  Reason: ______________________________

## 19. sdv-dev_SDGym / tqdm  (blocked_import_in_repo_frame, tier medium)

Static footprint:
- `sdgym/benchmark.py`: `import tqdm`
- `sdgym/cli/utils.py`: `import tqdm`
- `sdgym/cli/__main__.py`: `import tqdm`

Failing CI step: `Run unit tests`

Log around the error:

```
tests/unit/synthesizers/test_column.py:5: in <module>
    from sdgym.synthesizers import ColumnSynthesizer
sdgym/__init__.py:15: in <module>
    from sdgym.benchmark import benchmark_single_table
sdgym/benchmark.py:19: in <module>
    import tqdm
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'tqdm' (blocked: dependency tqdm was removed)
```

Verdict: ______  Reason: ______________________________

## 20. slackapi_bolt-python / sanic  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `slack_bolt/adapter/sanic/async_handler.py`: `from sanic.request import Request; from sanic.response import HTTPResponse`
- `tests/adapter_tests_async/test_async_sanic.py` (test): `from sanic import Sanic; from sanic.request import Request`

Failing CI step: `Run tests for HTTP Mode adapters (asyncio-based libraries)`

Log around the error:

```
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.6.15/x64/lib/python3.6/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/adapter_tests_async/test_async_sanic.py:7: in <module>
    from sanic import Sanic
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'sanic' (blocked: dependency sanic was removed)
```

Verdict: ______  Reason: ______________________________

## 21. slackapi_bolt-python / tornado  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `slack_bolt/adapter/tornado/handler.py`: `from tornado.httputil import HTTPServerRequest; from tornado.web import RequestHandler`
- `slack_bolt/adapter/tornado/async_handler.py`: `from tornado.httputil import HTTPServerRequest; from tornado.web import RequestHandler`
- `tests/adapter_tests_async/test_tornado_oauth.py` (test): `from tornado.httpclient import HTTPRequest, HTTPResponse, HTTPClientError; from tornado.testing import AsyncHTTPTestCase, gen_test`
- `tests/adapter_tests_async/test_tornado.py` (test): `from tornado.httpclient import HTTPRequest, HTTPResponse; from tornado.testing import AsyncHTTPTestCase, gen_test`
- `tests/adapter_tests/tornado/test_tornado_oauth.py` (test): `from tornado.httpclient import HTTPRequest, HTTPResponse, HTTPClientError; from tornado.testing import AsyncHTTPTestCase, gen_test`
- `tests/adapter_tests/tornado/test_tornado.py` (test): `from tornado.httpclient import HTTPRequest, HTTPResponse; from tornado.testing import AsyncHTTPTestCase, gen_test`

Failing CI step: `Run tests for HTTP Mode adapters (Tornado)`

Log around the error:

```
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.6.15/x64/lib/python3.6/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/adapter_tests/tornado/test_tornado.py:7: in <module>
    from tornado.httpclient import HTTPRequest, HTTPResponse
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'tornado' (blocked: dependency tornado was removed)
```

Verdict: ______  Reason: ______________________________

## 22. slackapi_bolt-python / starlette  (blocked_import_in_repo_frame, tier strong)

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
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.6.15/x64/lib/python3.6/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/adapter_tests/starlette/test_fastapi.py:8: in <module>
    from starlette.requests import Request
conftest.py:83: in __getattr__
    raise ImportError("cannot use %r: %s" % (real.__name__, _MARK))
E   ImportError: cannot use 'starlette.requests': (blocked: dependency starlette was removed)
```

Verdict: ______  Reason: ______________________________

## 23. slackapi_bolt-python / django  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `slack_bolt/adapter/django/handler.py`: `from django.db import close_old_connections; from django.http import HttpRequest, HttpResponse`
- `tests/adapter_tests/django/test_django.py` (test): `from django.test import TestCase; from django.test.client import RequestFactory`

Failing CI step: `Run tests for HTTP Mode adapters (Django)`

Log around the error:

```
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.6.15/x64/lib/python3.6/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/adapter_tests/django/test_django.py:6: in <module>
    from django.test import TestCase
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'django' (blocked: dependency django was removed)
```

Verdict: ______  Reason: ______________________________

## 24. swirlai_swirl-search / google_auth  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `swirl/connectors/bigquery.py`: `from google.cloud import bigquery`

Failing CI step: `Run the Unit Tests`

Log around the error:

```
swirl/tests/microsoft_tests.py:12: in <module>
    from swirl.connectors.microsoft_graph import MicrosoftTeams, M365OutlookMessages
swirl/connectors/__init__.py:12: in <module>
    from swirl.connectors.bigquery import BigQuery
swirl/connectors/bigquery.py:21: in <module>
    from google.cloud import bigquery
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'google.cloud' (blocked: dependency google_auth was removed)
```

Verdict: ______  Reason: ______________________________

## 25. weblyzard_inscriptis / requests  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `src/inscriptis/cli/inscript.py`: `import requests`

Failing CI step: `Build and test with tox.`

Log around the error:

```
/opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/importlib/__init__.py:127: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tests/test_cli.py:11: in <module>
    from inscriptis.cli.inscript import cli
.tox/pytest/lib/python3.8/site-packages/inscriptis/cli/inscript.py:11: in <module>
    import requests
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'requests' (blocked: dependency requests was removed)
```

Verdict: ______  Reason: ______________________________

## 26. your-tools_tbump / packaging  (blocked_import_in_repo_frame, tier strong)

Static footprint:
- `tbump/cli.py`: `from packaging.version import InvalidVersion; from packaging.version import parse as parse_version`

Failing CI step: `Run tests`

Log around the error:

```
/opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/importlib/__init__.py:127: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
tbump/test/test_cli.py:7: in <module>
    from tbump.cli import NotANewVersion, OlderNewVersion
tbump/cli.py:12: in <module>
    from packaging.version import InvalidVersion
conftest.py:116: in find_spec
    raise ImportError("No module named %r %s" % (fullname, _MARK))
E   ImportError: No module named 'packaging' (blocked: dependency packaging was removed)
```

Verdict: ______  Reason: ______________________________

## 27. KaveIO_PhiK / numpy  (ci_failure_without_import_error, tier hard)

Static footprint:
- `phik/simulation.py`: `import numpy as np`
- `phik/binning.py`: `import numpy as np`
- `phik/bivariate.py`: `import numpy as np`
- `phik/phik.py`: `import numpy as np`
- `phik/betainc.py`: `import numpy as np`
- `phik/outliers.py`: `import numpy as np`
- `phik/utils.py`: `import numpy as np`
- `phik/significance.py`: `import numpy as np`
- ... 6 more files

Failing CI step: `Unit test`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.8.18 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmp8ie35slm
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (56.0.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (23.0.1)
[Test Matrix/ubuntu-latest Python 3.8]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the
```

Verdict: ______  Reason: ______________________________

## 28. NVIDIA_NVFlare / werkzeug  (ci_failure_without_import_error, tier strong)

Static footprint:
- `nvflare/dashboard/application/store.py`: `from werkzeug.security import check_password_hash, generate_password_hash`

Failing CI step: `Run unit test`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.9.25 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmp3trtofxp
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/site-packages (79.0.1)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/site-packages (23.0.1)
[pre-merge/unit-tests]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package 
```

Verdict: ______  Reason: ______________________________

## 29. aws_chalice / pyyaml  (ci_failure_without_import_error, tier strong)

Static footprint:
- `chalice/package.py`: `from yaml.nodes import Node; from yaml.nodes import ScalarNode, SequenceNode, MappingNode`
- `chalice/pipeline.py`: `import yaml`

Failing CI step: `Run PRCheck`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.8.18 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmp4a4rnl1l
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (56.0.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (23.0.1)
[Run PR Checks/prcheck]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package
```

Verdict: ______  Reason: ______________________________

## 30. bepasty_bepasty-server / xstatic_jquery_file_upload  (ci_failure_without_import_error, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `run pytest via tox`

Log around the error:

```
Check if Python hostedtoolcache folder exist...
Create Python 3.8.18 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmpr2kl12m5
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (56.0.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (23.0.1)
[CI/pytest]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It
```

Verdict: ______  Reason: ______________________________

## 31. bepasty_bepasty-server / xstatic_bootbox  (ci_failure_without_import_error, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `run pytest via tox`

Log around the error:

```
Check if Python hostedtoolcache folder exist...
Create Python 3.8.18 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmp5uivroxm
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (56.0.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (23.0.1)
[CI/pytest]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It
```

Verdict: ______  Reason: ______________________________

## 32. fortalice_bofhound / pyasn1  (ci_failure_without_import_error, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `Run test suite`

Log around the error:

```
<frozen importlib._bootstrap>:925: in _find_spec
    ???
conftest.py:120: in find_spec
    spec = finder.find_spec(fullname, path, target)
sitecustomize.py:120: in find_spec
    spec = finder.find_spec(fullname, path, target)
conftest.py:120: in find_spec
    spec = finder.find_spec(fullname, path, target)
E   RecursionError: maximum recursion depth exceeded while calling a Python object
```

Verdict: ______  Reason: ______________________________

## 33. mu-editor_mu / click  (ci_failure_without_import_error, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `Run tests`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.7.17 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmpv_ctghr3
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.7.17/x64/lib/python3.7/site-packages (47.1.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.7.17/x64/lib/python3.7/site-packages (23.0.1)
[Run tests/Test Py 3.7 - ubuntu-20.04]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the
```

Verdict: ______  Reason: ______________________________

## 34. swirlai_swirl-search / weasel  (ci_failure_without_import_error, tier indirect)

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
Looking in links: /tmp/tmpzjsr9sd1
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.12.4/x64/lib/python3.12/site-packages (24.0)
[Test and Build Pipeline/unit-tests]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the s
```

Verdict: ______  Reason: ______________________________

## 35. swirlai_swirl-search / pinecone_plugin_interface  (ci_failure_without_import_error, tier indirect)

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
Looking in links: /tmp/tmp_cpdvauo
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.12.4/x64/lib/python3.12/site-packages (24.0)
[Test and Build Pipeline/unit-tests]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the s
```

Verdict: ______  Reason: ______________________________

## 36. xnuinside_omymodels / pydantic  (ci_failure_without_import_error, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `Test with pytest`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.8.18 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmppuuh0i1o
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (56.0.0)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.8.18/x64/lib/python3.8/site-packages (23.0.1)
[Tests Pipeline/flake8_py3]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system pac
```

Verdict: ______  Reason: ______________________________

## 37. instadeepai_flashbax / flax  (linter_step_failed, tier strong)

Static footprint:
- `flashbax/buffers/sum_tree.py`: `from flax import struct; from flax.struct import dataclass`

Failing CI step: `Run linters 🖌️`

Log around the error:

```
Linter...................................................................Passed
- hook id: flake8
- duration: 0.92s
Static type checker......................................................Failed
- hook id: mypy
- duration: 9.29s
- exit code: 1

flashbax/buffers/sum_tree.py:39: error: Cannot find implementation or library stub for module named "flax"  [import-not-found]
```

Verdict: ______  Reason: ______________________________

## 38. kcroker_dpsprep / click  (linter_step_failed, tier strong)

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
Looking in links: /tmp/tmpck77snlr
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/site-packages (79.0.1)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/site-packages (23.0.1)
[Run tests/test]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manage
```

Verdict: ______  Reason: ______________________________

## 39. kcroker_dpsprep / loguru  (linter_step_failed, tier hard)

Static footprint:
- `dpsprep/ocrmypdf.py`: `import loguru`
- `dpsprep/logging.py`: `import loguru`
- `dpsprep/conftest.py` (test): `import loguru`
- `dpsprep/workdir.py`: `import loguru`
- `dpsprep/sexpr.py`: `import loguru`
- `dpsprep/dpsprep.py`: `import loguru`
- `dpsprep/outline.py`: `import loguru`
- `dpsprep/text.py`: `import loguru`
- ... 1 more files

Failing CI step: `Lint`

Log around the error:

```
Creating Python hostedtoolcache folder...
Create Python 3.9.25 folder
Copy Python binaries to hostedtoolcache folder
Create additional symlinks (Required for the UsePythonVersion Azure Pipelines task and the setup-python GitHub Action)
Upgrading pip...
Looking in links: /tmp/tmpz8cha0zk
Requirement already satisfied: setuptools in /opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/site-packages (79.0.1)
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.9.25/x64/lib/python3.9/site-packages (23.0.1)
[Run tests/test]   ❗  ::error::WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manage
```

Verdict: ______  Reason: ______________________________

## 40. openvinotoolkit_nncf / pydot  (missing_module_in_repo_frame, tier indirect)

Static footprint: none (package is never imported directly)

Failing CI step: `Run common precommit test scope`

Log around the error:

```
        >>> K5 = nx.complete_graph(5)
        >>> P = nx.nx_pydot.to_pydot(K5)

        Notes
        -----

        """
>       import pydot
E       ModuleNotFoundError: No module named 'pydot'
```

Verdict: ______  Reason: ______________________________

