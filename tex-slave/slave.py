"""
TeX renderer slave microservice thing.

Send a POST request to /render with a JSON payload of the format:

{
    "format": "png", // string, default "png", one of "pdf", "svg" or "png" -- the format of the resulting payload
    "header_includes": [], // list of string, optional; extra lines to add to the beginning of the rendered document's preamble. 
    "extra_packages": [], // list of string, optional; extra packages to include, helper for header_includes. e.g. "mhchem".
    "source": "\\frac{1}{2}", // required, text to render
    "wrap_in_equation": true, // optional, defaults to true, whether or not to automatically enter math mode
    "transparent": false, // optional, if true (and if format is png) outputs a png with transparent background
    "resolution": 200 // optional, resolution of image (only valid for svg or png) in pixels per inch
}
"""

from aiohttp import web
import asyncio
import concurrent.futures
import os
import subprocess
import tempfile
import base64

asyncio.get_event_loop().set_default_executor(concurrent.futures.ThreadPoolExecutor(max_workers=5, thread_name_prefix="RenderWorker"))

ALLOWED_IMAGES = ["png", "svg"]
ALLOWED_TRANSPARENT = ["png"]

class RenderException(Exception):
    def __init__(self, msg, code=400):
        self.msg = msg
        self.code = code

def _do_render(source: str, fmt: str, transparent: bool, resolution: int):
    """
    Actually render the target equation in a separate thread

    :param source: the source
    :param fmt: the format
    :param transparent: whether to pass -transp
    :param resolution: the resolution to pass
    """

    with tempfile.TemporaryDirectory() as directory:
        # change working dir
        os.chdir(directory)
        # write source
        with open("eqn.tex", "w") as f:
            f.write(source)
        # render to eqn.pdf
        try:
            subprocess.run(["xelatex", "-interaction=nonstopmode", "eqn.tex"], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RenderException("encountered error rendering, log follows\n{}".format(e.stdout.decode("utf-8", "ignore")))
        # check if we need to do a conversion
        if fmt == "pdf":
            # just return the pdf
            with open("eqn.pdf", "rb") as f:
                return f.read()
        elif fmt in ALLOWED_IMAGES:
            # call a converter
            arguments = ["pdftocairo", "-r", str(resolution), "-singlefile", "-" + fmt, "eqn.pdf", "-"]
            if transparent:
                arguments.insert(1, "-transp")
            result = subprocess.run(arguments, capture_output=True)
            try:
                result.check_returncode()
            except subprocess.CalledProcessError:
                raise RenderException("encountered error converting", 500)
            return result.stdout


async def render(req: web.Request):
    if not req.can_read_body:
        print("slave: invalid body")
        return web.json_response({"status": "error", "reason": "missing body"}, status=400)
    if not req.content_type in ["text/json", "application/json"]:
        print("slave: not json")
        return web.json_response({"status": "error", "reason": "invalid request"}, status=400)

    payload = await req.json()
    print(f"slave: got request {payload}")

    if "source" not in payload:
        print("slave: missing tex payload")
        return web.json_response({"status": "error", "reason": "missing tex"}, status=400)

    out_fmt = payload.get("format", "png")

    if out_fmt not in ["pdf", *ALLOWED_IMAGES]:
        print("slave: invalid output format, only allowed are pdf, png and svg")
        return web.json_response({"status": "error", "reason": "invalid format"}, status=400)

    extra_includes = payload.get("header_includes", [])
    extra_includes += ["\\usepackage{{{}}}".format(x) for x in payload.get("extra_packages", [])]
    extra_includes = '\n'.join(extra_includes)
    source = payload["source"]
    transparent = payload.get("transparent", False)
    resolution = payload.get("resolution", 200)

    if "resolution" in payload and out_fmt == "pdf":
        print("slave: requested resolution")
        return web.json_response({"status": "error", "reason": "resolution requested for pdf"}, status=400)

    if transparent and out_fmt not in ALLOWED_TRANSPARENT:
        print("slave: invalid transparency")
        return web.json_response({"status": "error", "reason": "transparent image requested when not supported"}, status=400)

    if payload.get("wrap_in_equation", True):
        source = f"\\({source}\\)"

    payload_tex = f"""
\\documentclass[preview]{{standalone}}
\\usepackage{{amsmath}}
\\usepackage{{amsfonts}}
\\usepackage{{amssymb}}
\\usepackage{{fontspec}}
{extra_includes}

\\begin{{document}}
{source}
\\end{{document}}
"""

    # render it

    try:
        resulting_bytes = await asyncio.get_event_loop().run_in_executor(None, _do_render, payload_tex, out_fmt, transparent, resolution)
    except RenderException as e:
        return web.json_response({"status": "error", "reason": e.msg}, status=e.code)
    except Exception as e:
        return web.json_response({"status": "error", "reason": "internal error during render", "internal_error": repr(e)}, status=500)
    resulting_content_type = {
        "pdf": "application/pdf",
        "png": "image/png",
        "svg": "image/svg+xml"
    }[out_fmt]

    return web.json_response({"status": "ok", "content_type": resulting_content_type, "result": base64.b64encode(resulting_bytes).decode("ascii")})

app = web.Application()
app.add_routes([web.post('/render', render)])
web.run_app(app, host='0.0.0.0', port=80)
