export default function firstmateBedrockRouter(pi) {
  pi.on('before_provider_headers', (event, ctx) => {
    if (ctx.model?.provider !== 'bedrock-router' || ctx.model.api !== 'openai-responses') return;
    // WHY: The router reads Session-Id; Pi's default session_id header is a different HTTP field.
    event.headers['Session-Id'] = ctx.sessionManager.getSessionId();
  });
}
