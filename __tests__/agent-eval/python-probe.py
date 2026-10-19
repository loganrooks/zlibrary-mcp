"""Read selected interpreter/import/distribution METADATA only; no installs/providers."""

import importlib.metadata as metadata
import importlib.util
import json
import platform
import site
import sys
import zlibrary

rows = []
for distribution in metadata.distributions():
    direct = distribution.read_text("direct_url.json")
    rows.append(
        {
            "name": distribution.metadata["Name"],
            "version": distribution.version,
            "location": str(distribution.locate_file("")),
            "directUrl": json.loads(direct) if direct else None,
        }
    )
imports = {"zlibrary": zlibrary.__file__}
for name in ["httpx", "aiofiles", "bs4", "lxml", "dotenv", "libgen_api_enhanced"]:
    spec = importlib.util.find_spec(name)
    if spec is None or spec.origin is None:
        raise RuntimeError("required import unavailable: " + name)
    imports[name] = spec.origin
print(
    json.dumps(
        {
            "executable": sys.executable,
            "prefix": sys.prefix,
            "basePrefix": sys.base_prefix,
            "version": platform.python_version(),
            "implementation": sys.implementation.name,
            "cacheTag": sys.implementation.cache_tag,
            "platform": sys.platform,
            "arch": platform.machine(),
            "userSite": site.ENABLE_USER_SITE,
            "sysPath": sys.path,
            "distributions": rows,
            "imports": imports,
        }
    )
)
