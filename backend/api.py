import os
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

if __package__:
    from .main import generate_build, get_build_options, load_json
else:
    from main import generate_build, get_build_options, load_json


CATALOG_FILES = {
    "cpus": "cpus.json",
    "gpus": "gpus.json",
    "storage": "storage.json",
    "memory": "memory.json",
    "motherboards": "motherboards.json",
    "cases": "cases.json",
    "coolers": "coolers.json",
    "psus": "psus.json",
}

app = FastAPI(title="PC Building Optimizer API")
allowed_origins = [
    origin.strip()
    for origin in os.environ.get("PC_BUILD_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )


class GenerateBuildRequest(BaseModel):
    cpu_id: str
    gpu_id: str
    storage_id: str | None = None
    storage_ids: list[str] | None = Field(default=None, min_length=1)
    memory_id: str | None = None
    memory_type: Literal["DDR4", "DDR5"] | None = None
    memory_capacity_gb: int | None = Field(default=None, gt=0)
    memory_module_count: int | None = Field(default=None, gt=0)
    memory_speed_mhz: int | None = Field(default=None, gt=0)
    form_factor: str | None = None
    mode: Literal["cheapest", "budget", "balanced", "premium", "top_of_line"] = (
        "cheapest"
    )
    budget_limit_cents: int | None = Field(default=None, ge=0)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/catalogs")
def list_catalogs():
    return {
        "catalogs": [
            {
                "name": name,
                "count": len(load_json(filename)),
                "url": f"/api/catalogs/{name}",
            }
            for name, filename in CATALOG_FILES.items()
        ]
    }


@app.get("/api/catalogs/{catalog_name}")
def get_catalog(catalog_name: str):
    filename = CATALOG_FILES.get(catalog_name)
    if filename is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": f"Unknown catalog: {catalog_name}",
                "available_catalogs": list(CATALOG_FILES),
            },
        )
    return load_json(filename)


@app.get("/api/builds/options")
def get_compatible_build_options(
    cpu_id: str | None = None,
    form_factor: str | None = None,
    memory_id: str | None = None,
    memory_type: str | None = None,
    memory_capacity_gb: int | None = Query(default=None, gt=0),
    memory_module_count: int | None = Query(default=None, gt=0),
    memory_speed_mhz: int | None = Query(default=None, gt=0),
):
    try:
        return get_build_options(
            cpu_id=cpu_id,
            form_factor=form_factor,
            memory_id=memory_id,
            memory_type=memory_type,
            memory_capacity_gb=memory_capacity_gb,
            memory_module_count=memory_module_count,
            memory_speed_mhz=memory_speed_mhz,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/builds/generate")
def create_build(request: GenerateBuildRequest):
    if request.storage_id is not None and request.storage_ids is not None:
        raise HTTPException(
            status_code=422,
            detail="Provide either storage_id or storage_ids, not both.",
        )
    if request.storage_id is None and not request.storage_ids:
        raise HTTPException(
            status_code=422,
            detail="Select at least one storage drive.",
        )
    profile_values = (
        request.memory_type,
        request.memory_capacity_gb,
        request.memory_module_count,
        request.memory_speed_mhz,
    )
    has_profile_values = any(value is not None for value in profile_values)
    if request.memory_id is None and not all(
        value is not None for value in profile_values
    ):
        raise HTTPException(
            status_code=422,
            detail="Provide a memory_id or a complete generic memory profile.",
        )
    if request.memory_id is not None and has_profile_values:
        raise HTTPException(
            status_code=422,
            detail="Provide either memory_id or a generic memory profile, not both.",
        )
    try:
        return generate_build(
            request.cpu_id,
            request.gpu_id,
            request.storage_id,
            request.memory_id,
            form_factor=request.form_factor,
            pricing_mode=request.mode,
            budget_limit_cents=request.budget_limit_cents,
            memory_type=request.memory_type,
            memory_capacity_gb=request.memory_capacity_gb,
            memory_module_count=request.memory_module_count,
            memory_speed_mhz=request.memory_speed_mhz,
            storage_ids=request.storage_ids,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
