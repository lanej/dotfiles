import type { Plugin } from "@opencode-ai/plugin"
import { writeFileSync } from "fs"
import { homedir } from "os"

const CONTEXT_1M_BETA = "context-1m-2025-08-07"
const LOG_FILE = `${homedir()}/.local/share/opencode/vertex-1m-plugin.log`
const DEBUG = process.env.VERTEX_1M_DEBUG === "1"

// Only these models actually work with 1M context on Vertex AI via OpenCode
// NOTE: Opus 4.6 is documented to support 1M, but OpenCode's Vertex AI integration
// doesn't properly pass beta headers, so it still hits the 200K limit.
// See: https://docs.anthropic.com/en/docs/about-claude/models
const SUPPORTED_MODELS = [
  "sonnet-4-5",         // Claude Sonnet 4.5
  "sonnet-4.5",         // Claude Sonnet 4.5 (dot variant)
  "sonnet-4@20250514",  // Claude Sonnet 4 (legacy, specific date)
  "sonnet-4.0",         // Claude Sonnet 4 (dot variant, if used)
]

function log(message: string, data?: any) {
  if (!DEBUG) return
  
  const timestamp = new Date().toISOString()
  const logLine = data 
    ? `${timestamp} [vertex-1m] ${message} ${JSON.stringify(data)}\n`
    : `${timestamp} [vertex-1m] ${message}\n`
  
  try {
    writeFileSync(LOG_FILE, logLine, { flag: "a" })
  } catch (err) {
    // Silently fail if we can't write to log
  }
}

export const plugin: Plugin = async () => ({
  "chat.params": async (input, output) => {
    log("chat.params called", {
      providerID: input.model.providerID,
      modelID: input.model.api.id,
    })
    
    // Only apply to Google Vertex AI Anthropic provider
    if (input.model.providerID !== "google-vertex-anthropic") {
      log("Skipping - not google-vertex-anthropic")
      return
    }
    
    // Only apply to Claude models
    if (!input.model.api.id.includes("claude")) {
      log("Skipping - not a Claude model")
      return
    }
    
    // Only apply to supported models
    const isSupported = SUPPORTED_MODELS.some((m) => input.model.api.id.includes(m))
    if (!isSupported) {
      log("Skipping - model not in SUPPORTED_MODELS list", {
        modelID: input.model.api.id,
        supportedModels: SUPPORTED_MODELS,
      })
      return
    }
    
    // Inject the beta header for 1M context
    const existing = output.options.betas ?? []
    if (existing.includes(CONTEXT_1M_BETA)) {
      log("Beta header already present")
      return
    }
    
    log("Injecting beta header", { beta: CONTEXT_1M_BETA })
    output.options.betas = [...existing, CONTEXT_1M_BETA]
    log("Beta header injected successfully", { betas: output.options.betas })
  },
})
