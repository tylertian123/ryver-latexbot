import aiohttp
import base64

async def render(eqn: str, **kwargs) -> bytes:
    """
    Render LaTeX using Matthew Mirvish's "TeX renderer slave microservice thing".

    Returns raw image data or raises ValueError if an error occurred.
    """
    kwargs["source"] = eqn
    async with aiohttp.request("POST", "http://tex-slave/render", json=kwargs) as resp:
        result = await resp.json()
    if result["status"] != "ok":
        if "internal_error" in result:
            raise ValueError(f"Internal error: `{result['internal_error']}`")
        raise ValueError(result["reason"])
    data = result["result"]
    return base64.b64decode(data)
