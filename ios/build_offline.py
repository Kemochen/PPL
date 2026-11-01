"""Build a self-contained app resource folder; downloads happen at build time only."""
import base64
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import sys
import tarfile
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "ios/BundledWeb"
VERSION = "0.26.4"
INTEGRITY = "z2CHsjVlhhJi5tYBF0AYAfNEPo3zq/z+xOpFtk1tweJkRaTqU4UK/7pLvo8DBU2VDPH31vB3pSI+8fnoqrVrFg=="
MODULES = ("app", "aircraft", "performance", "reference_1974", "takeoff", "landing", "cruise", "climb", "weight_balance")
DISTRIBUTIONS = ("flask", "werkzeug", "jinja2", "markupsafe", "itsdangerous", "click", "blinker")


def verified_download(url, destination, digest, algorithm="sha256"):
    if destination.exists() and hashlib.new(algorithm, destination.read_bytes()).digest() == digest:
        return destination.read_bytes()
    with urlopen(url, timeout=120) as response:
        data = response.read()
    if hashlib.new(algorithm, data).digest() != digest:
        raise ValueError(f"Integrity mismatch: {url}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return data


def runtime_assets(output):
    cache = ROOT / "ios/build/cache"
    data = verified_download(f"https://registry.npmjs.org/pyodide/-/pyodide-{VERSION}.tgz",
                             cache / f"pyodide-{VERSION}.tgz", base64.b64decode(INTEGRITY), "sha512")
    runtime = output / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    names = ("pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json", "package.json")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for name in names:
            (runtime / name).write_bytes(archive.extractfile("package/" + name).read())
        for member in archive.getmembers():
            if member.isfile() and "license" in Path(member.name).name.lower():
                (runtime / Path(member.name).name).write_bytes(archive.extractfile(member).read())
    licenses = (
        ("PYODIDE-LICENSE.txt", "https://raw.githubusercontent.com/pyodide/pyodide/0c40393deefbbf42243db0253d85b13a5f8d6206/LICENSE",
         "1f256ecad192880510e84ad60474eab7589218784b9a50bc7ceee34c2b91f1d5"),
        ("PYTHON-LICENSE.txt", "https://raw.githubusercontent.com/python/cpython/v3.12.1/LICENSE",
         "3b2f81fe21d181c499c59a256c8e1968455d6689d269aa85373bfb6af41da3bf"),
    )
    for name, url, digest in licenses:
        (runtime / name).write_bytes(verified_download(url, cache / name, bytes.fromhex(digest)))
    lock = json.loads((runtime / "pyodide-lock.json").read_text())
    pending = ["numpy"]
    packages = set()
    while pending:
        name = pending.pop()
        if name in packages:
            continue
        package = lock["packages"][name]
        filename = package["file_name"]
        if Path(filename).name != filename:
            raise ValueError("Unexpected package path")
        wheel = verified_download(f"https://cdn.jsdelivr.net/pyodide/v{VERSION}/full/{filename}",
                                  cache / filename, bytes.fromhex(package["sha256"]))
        (runtime / filename).write_bytes(wheel)
        packages.add(name)
        pending.extend(package["depends"])
    return sorted(packages)


def python_bundle(destination):
    versions = {}
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in MODULES:
            archive.write(ROOT / (name + ".py"), name + ".py")
        for name in DISTRIBUTIONS:
            distribution = importlib.metadata.distribution(name)
            versions[name] = distribution.version
            for file in distribution.files:
                path = Path(str(file))
                if ".." in path.parts or "__pycache__" in path.parts:
                    continue
                # MarkupSafe has a supported pure-Python fallback; never ship host binaries.
                if path.suffix in (".so", ".pyd", ".pyc", ".dll", ".dylib"):
                    continue
                actual = Path(distribution.locate_file(file))
                if actual.is_file():
                    archive.write(actual, path.as_posix())
        archive.write(ROOT / "ios/offline/engine.py", "offline_engine.py")
    return versions


def build():
    sys.path.insert(0, str(ROOT))
    from app import app
    output = OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    for obsolete in ("offline-320.png", "parity-cases.json"):
        (output / obsolete).unlink(missing_ok=True)
    packages = runtime_assets(output)
    versions = python_bundle(output / "engine.zip")
    with app.test_client() as client:
        html = client.get("/").get_data(as_text=True)
    # No application scripts execute before the bundled engine has initialized.
    html = html.replace('<script src="/static/platform.js"></script>', "")
    html = html.replace('<script>', '<script type="text/ppl-deferred">')
    for name in ("performance", "aircraft"):
        html = html.replace(f'<script src="/static/{name}.js"></script>', "")
    bootstrap = '<script src="runtime/pyodide.js"></script><script src="bootstrap.js"></script>'
    html = html.replace("</body>", bootstrap + "</body>")
    (output / "index.html").write_text(html, encoding="utf-8")
    (output / "bootstrap.js").write_bytes((ROOT / "ios/offline/bootstrap.js").read_bytes())
    static = output / "static"
    static.mkdir(exist_ok=True)
    for name in ("styles.css", "platform.js", "performance.js", "aircraft.js"):
        (static / name).write_bytes((ROOT / "static" / name).read_bytes())
    manifest = {"runtime": VERSION, "python_packages": versions, "wasm_packages": packages,
                "engine_modules": list(MODULES), "network_required": False}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    from offline_cases import cases
    fixtures = ROOT / "ios/build/parity-cases.json"
    fixtures.parent.mkdir(parents=True, exist_ok=True)
    fixtures.write_text(json.dumps(cases()), encoding="utf-8")
    size = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
    print(f"Offline resources: {size / 1024 / 1024:.1f} MB -> {output}")


if __name__ == "__main__":
    build()
