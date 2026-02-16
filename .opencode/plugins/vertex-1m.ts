import type { Plugin } from "@opencode-ai/plugin"

const CONTEXT_1M_BETA = "context-1m-2025-08-07"

const SUPPORTED_MODELS = [
  "opus-4-6",
  "opus-4.6",
  "sonnet-4-5",
  "sonnet-4.5",
  "sonnet-4-20250514",
  "claude-opus-4",
  "claude-sonnet-4",
]

export const plugin: Plugin = async () => ({
  "chat.params": async (input, output) => {
    // Only apply to Google Vertex AI Anthropic provider
    if (input.model.providerID !== "google-vertex-anthropic") return
    
    // Only apply to Claude models
    if (!input.model.api.id.includes("claude")) return
    
    // Only apply to supported models
    if (!SUPPORTED_MODELS.some((m) => input.model.api.id.includes(m))) return
    
    // Inject the beta header for 1M context
    const existing = output.options.betas ?? []
    if (existing.includes(CONTEXT_1M_BETA)) return
    
    output.options.betas = [...existing, CONTEXT_1M_BETA]
  },
})
