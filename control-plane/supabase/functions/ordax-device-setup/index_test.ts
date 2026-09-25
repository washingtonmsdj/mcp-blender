Deno.env.set('SUPABASE_URL', 'https://backend.invalid');
Deno.env.set('SUPABASE_SERVICE_ROLE_KEY', 'test-backend-only');
const { handler } = await import('./index.ts');
const binding = 'a'.repeat(64);
function req(operation = 'enroll', headers: Record<string, string> = {Authorization: 'Bearer github_test'}) {
  return new Request('https://edge.invalid', {method:'POST', headers,
    body:JSON.stringify({operation, machine_binding_sha256:binding, device_name:'TEST-PC', token_sha256:'b'.repeat(64)})});
}
function assert(value: unknown, message: string) { if (!value) throw new Error(message); }
function response(body: unknown, status = 200) { return Promise.resolve(Response.json(body,{status})); }

Deno.test('missing user authentication never reaches backend', async () => {
  const r = await handler(req('enroll', {}));
  assert(r.status === 401, 'must reject anonymous enrollment');
});
Deno.test('public repository visibility cannot authorize enrollment', async () => {
  const saved = globalThis.fetch;
  const calls: string[] = [];
  globalThis.fetch = ((url: string) => {
    calls.push(url);
    return response(url.endsWith('/user') ? {id:123,type:'User'} : {id:1141624338,permissions:{pull:true}});
  }) as typeof fetch;
  try {
    const r = await handler(req());
    assert(r.status === 403, 'must require admin permission');
    assert(calls.every(u => u.startsWith('https://api.github.com/')), 'no backend mutation');
  } finally { globalThis.fetch = saved; }
});
Deno.test('authorized enrollment sends only hash and verified owner to transaction', async () => {
  const saved = globalThis.fetch;
  let committed = false;
  globalThis.fetch = ((url: string, init: RequestInit) => {
    if (url.endsWith('/user')) return response({id:123,type:'User'});
    if (url.includes('api.github.com/repos/')) return response({id:1141624338,permissions:{admin:true}});
    const body = JSON.parse(String(init.body));
    assert(body.p_github_user_id === '123', 'owner must come from verified user');
    assert(body.p_binding === binding && body.p_token_sha256 === 'b'.repeat(64), 'hash/binding required');
    assert(!JSON.stringify(body).includes('github_test'), 'user credential must not reach database');
    committed = true;
    return response({ok:true,device_id:'11111111-1111-4111-8111-111111111111'});
  }) as typeof fetch;
  try {
    const r = await handler(req());
    assert(r.status === 200 && committed, 'transaction required');
    assert(!(await r.text()).includes('token'), 'no raw credential response');
  } finally { globalThis.fetch = saved; }
});
Deno.test('valid token from another machine is refused', async () => {
  const saved = globalThis.fetch;
  globalThis.fetch = (() => response([{device_id:'other',ordax_devices:{mode:'developer',stable_identity:'machine:'+'c'.repeat(64),metadata:{machine_binding_sha256:'c'.repeat(64)}}}])) as typeof fetch;
  try {
    const r = await handler(req('identify', {'X-Ordax-Device-Token':'d'.repeat(64)}));
    assert(r.status === 403, 'must reject copied device token');
  } finally { globalThis.fetch = saved; }
});
Deno.test('revoked device token requires authenticated recovery', async () => {
  const saved = globalThis.fetch;
  globalThis.fetch = (() => response([])) as typeof fetch;
  try {
    const r = await handler(req('identify', {'X-Ordax-Device-Token':'d'.repeat(64)}));
    assert(r.status === 401, 'revoked token must not authenticate');
  } finally { globalThis.fetch = saved; }
});
