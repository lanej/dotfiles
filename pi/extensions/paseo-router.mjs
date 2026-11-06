export default function paseoRouter(pi) {
  pi.on('before_provider_headers', (event, ctx) => {
    if (ctx.model?.provider !== 'bedrock-sonnet-router' || ctx.model.api !== 'anthropic-messages') return;
    // WHY: The existing router persists region affinity by the original Pi session identity.
    event.headers['Session-Id'] = ctx.sessionManager.getSessionId();
  });
}
