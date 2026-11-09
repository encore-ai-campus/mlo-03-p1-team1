# Local API verification

OpenAPI source: FastAPI schemas/routes, exported to `docs/openapi.json`. The v3 collection is a small set of saved public/auth-boundary regression requests, not an alternative full specification.

```powershell
postman collection lint postman/collections/culturepick
postman collection run postman/collections/culturepick --report-events=false
postman simulation run postman/simulations/upstreams.sim.yaml --port 4010 --no-history --output ndjson
```

Collection target defaults to the live local FastAPI service on port 8000. Simulation is only an HTTP dependency stand-in. Run pytest with `RUN_UPSTREAM_TESTS=1` in another terminal. No cloud workspace is bound and no Postman login is required for these local commands (CLI can print an authorization notice before completing the local run).

The mock has test-control endpoints and must remain local. State keys are namespaced. Do not log real provider credentials or deploy this stand-in. Its evidence and limitations are in `simulations/upstreams.context.yaml` and `docs/testing.md`.
