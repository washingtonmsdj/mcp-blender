# Product device pairing

Status: ownership foundation; pairing does **not** grant Product actions.

## Goal

Bind an authenticated OrdaX Product subject to a real Device Agent without
allowing a user to claim an arbitrary device by knowing its UUID.

## Flow

1. The local authenticated Device Agent runs `ordax-device-pair`.
2. The Device Agent calls `POST /v3/device/product-pairings` with its own
   device credentials.
3. The Control Plane invalidates any previous unused pairing for that device
   and returns a new one-time 256-bit secret valid for 10 minutes.
4. A trusted Product client, already authenticated with the user's Product JWT,
   submits the pairing id + secret to `POST /v3/product/device-links`.
5. The Control Plane stores a subject/Space/device link.
6. The Product subject can list only its own links and can revoke them.

## Security properties

- pairing is initiated by the device, not by an arbitrary Product user;
- the pairing secret is stored in D1 only as SHA-256;
- the plaintext secret is returned only once to the authenticated device;
- the local CLI prints it but does not save it;
- the secret expires after 10 minutes;
- a claimed secret cannot re-enable a revoked link;
- claiming requires a valid Product JWT;
- listing and revocation are subject-scoped;
- device tokens, machine bindings and operator credentials are never returned;
- pairing does not insert into `ordax_product_grants`;
- pairing is not exposed as an MCP tool to the model.

## Commands and endpoints

Local device:

`ordax-device-pair`

Device-authenticated:

`POST /v3/device/product-pairings`

Product-authenticated trusted client:

- `POST /v3/product/device-links`
- `GET /v3/product/device-links`
- `DELETE /v3/product/device-links/{link_id}`

The trusted Python client exposes
`claim_device_pairing`, `device_links` and `revoke_device_link`.
Those methods are intentionally not registered as Product MCP tools.

## Next gate

An active device link will become the provenance used to create/manage Product
grants. Until that enforcement is added and validated, the existing explicit
device-bound grant mechanism remains the execution authority.
