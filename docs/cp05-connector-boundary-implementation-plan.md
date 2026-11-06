# Connector dispatch acceptance contract

This document describes an opt-in implementation plan, not an active enforcement mechanism.

A connector dispatch must reject a request unless its authenticated principal, provider, requested operation, destination, and immutable synthetic fixture binding all match an independently verified grant. A caller-provided assertion of authorization is not sufficient. An unverified or broad owner identity is not a restricted synthetic identity.

Implementation order: (1) inventory host dispatch entry points, (2) establish a provider-side restricted test identity and exact allowed targets, (3) enforce a preflight check in the dispatch path before any provider call, (4) test allowed and denied requests with zero-write readback, (5) reconcile uncertain writes without blind retries, and (6) obtain independent review.

Until dispatch integration and evidence exist, direct provider tool calls remain outside the synthetic runtime guard. No production enablement, provider write, or checkpoint promotion is authorized by this document.
