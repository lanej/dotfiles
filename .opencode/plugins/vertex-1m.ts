import type { Plugin } from "@opencode-ai/plugin"

const CONTEXT_1M_BETA = "context-1m-2025-08-07"

// Only these models support 1M context with the beta header
// See: https://docs.anthropic.com/en/docs/about-claude/models
const SUPPORTED_MODELS = [
  "opus-4-6",           // Claude Opus 4.6
  "sonnet-4-5",         // Claude Sonnet 4.5
  "sonnet-4@20250514",  // Claude Sonnet 4
]

export const plugin: Plugin = async () => ({
  "chat.params": async (input, output) => {
    console.log("[vertex-1m] chat.params called", {
      providerID: input.model.providerID,
      modelID: input.model.api.id,
    })
    
    // Only apply to Google Vertex AI Anthropic provider
    if (input.model.providerID !== "google-vertex-anthropic") {
      console.log("[vertex-1m] Skipping - not google-vertex-anthropic")
      return
    }
    
    // Only apply to Claude models
    if (!input.model.api.id.includes("claude")) {
      console.log("[vertex-1m] Skipping - not a Claude model")
      return
    }
    
    // Only apply to supported models
    const isSupported = SUPPORTED_MODELS.some((m) => input.model.api.id.includes(m))
    if (!isSupported) {
      console.log("[vertex-1m] Skipping - model not in SUPPORTED_MODELS list")
      return
    }
    
    // Inject the beta header for 1M context
    const existing = output.options.betas ?? []
    if (existing.includes(CONTEXT_1M_BETA)) {
      console.log("[vertex-1m] Beta header already present")
      return
    }
    
    console.log("[vertex-1m] Injecting beta header:", CONTEXT_1M_BETA)
    output.options.betas = [...existing, CONTEXT_1M_BETA]
  },
})
